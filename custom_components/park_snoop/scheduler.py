"""Cancellable, deduplicated monitoring scheduler for one config entry."""

from __future__ import annotations

import asyncio
import heapq
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import TYPE_CHECKING

from custom_components.park_snoop.models import ProviderOutcome, ProviderResult
from custom_components.park_snoop.providers.base import (
    ProviderFormatError,
    ProviderRateLimitError,
    ProviderTransientError,
)

if TYPE_CHECKING:
    from custom_components.park_snoop.models import Plate
    from custom_components.park_snoop.providers.registry import ProviderRegistry

JobKey = tuple[str, str]
ResultListener = Callable[[tuple[ProviderResult, ...]], Awaitable[None] | None]


@dataclass(order=True, slots=True)
class _DueJob:
    """Heap entry whose sequence makes same-time jobs deterministic."""

    due_at: datetime
    sequence: int
    key: JobKey = field(compare=False)
    plate: Plate = field(compare=False)
    retry_attempt: int = field(compare=False, default=0)


class MonitoringScheduler:
    """Own all provider work for one entry and never duplicate a job key."""

    def __init__(
        self,
        registry: ProviderRegistry,
        result_listener: ResultListener,
        now: Callable[[], datetime] | None = None,
        jitter_seconds: Callable[[], float] | None = None,
    ) -> None:
        """Create a stopped scheduler with injected providers and result sink."""
        self._registry = registry
        self._result_listener = result_listener
        self._now = now or (lambda: datetime.now(UTC))
        self._jitter_seconds = jitter_seconds or (lambda: 0)
        self._queue: list[_DueJob] = []
        self._pending: dict[JobKey, _DueJob] = {}
        self._running: set[JobKey] = set()
        self._sequence = count()
        self._wake = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    @property
    def is_running(self) -> bool:
        """Return whether the entry-owned loop is active."""
        return self._task is not None and not self._task.done()

    @property
    def pending_keys(self) -> tuple[JobKey, ...]:
        """Return keys with queued or running work, without exposing heap entries."""
        return tuple(self._pending)

    @property
    def next_due_at(self) -> datetime | None:
        """Return the earliest non-stale due time for diagnostics and tests."""
        active_jobs = [job for job in self._queue if self._pending.get(job.key) is job]
        return min((job.due_at for job in active_jobs), default=None)

    def async_start(self) -> None:
        """Start the single cancellable entry task exactly once."""
        if not self.is_running:
            self._task = asyncio.create_task(self._async_loop())

    async def async_stop(self) -> None:
        """Cancel work waiting for this entry and await its scheduler task."""
        task = self._task
        self._task = None
        self._queue.clear()
        self._pending.clear()
        self._wake.set()
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def async_schedule(
        self, plate: Plate, provider_id: str, due_at: datetime
    ) -> None:
        """Schedule one key unless it already has queued or running work."""
        key = (plate.identifier, provider_id)
        if key in self._pending:
            return
        self._enqueue(key, plate, due_at)

    async def async_request_now(self, plate: Plate, provider_id: str) -> None:
        """Prioritize an idle key without duplicating queued or running work."""
        key = (plate.identifier, provider_id)
        if key in self._running:
            return
        existing = self._pending.get(key)
        if existing is not None:
            self._enqueue(key, plate, self._now())
            return
        self._enqueue(key, plate, self._now())

    async def async_run_due(self) -> None:
        """Dispatch all work that is due now; exposed for deterministic tests."""
        due_jobs: list[_DueJob] = []
        while self._queue and self._queue[0].due_at <= self._now():
            job = heapq.heappop(self._queue)
            if self._pending.get(job.key) is not job:
                continue
            due_jobs.append(job)

        jobs_by_provider: dict[str, list[_DueJob]] = {}
        for job in due_jobs:
            jobs_by_provider.setdefault(job.key[1], []).append(job)
        for provider_id, jobs in jobs_by_provider.items():
            provider = self._registry.get(provider_id)
            permitted_at = provider.rate_limit_policy.next_permitted_at(self._now())
            if permitted_at > self._now():
                self._async_requeue(jobs, permitted_at)
                continue
            if provider.metadata.supports_batching:
                await self._async_dispatch(provider_id, jobs)
                continue
            for job in jobs:
                await self._async_dispatch(provider_id, [job])

    async def _async_dispatch(self, provider_id: str, jobs: list[_DueJob]) -> None:
        """Run one provider request and retire all its represented job keys."""
        for job in jobs:
            self._running.add(job.key)
        retry_at: datetime | None = None
        try:
            provider = self._registry.get(provider_id)
            provider.rate_limit_policy.record_request(self._now())
            plates = tuple(job.plate.identifier for job in jobs)
            results = await provider.async_query(plates)
            callback_result = self._result_listener(results)
            if callback_result is not None:
                await callback_result
        except ProviderRateLimitError as error:
            retry_after = max(60, error.retry_after_seconds or 0)
            retry_at = self._now() + timedelta(seconds=retry_after)
            await self._async_publish_error(
                jobs, ProviderOutcome.RATE_LIMITED, retry_after, "rate limited"
            )
        except ProviderTransientError:
            retry_at = self._now() + timedelta(
                seconds=min(15 * 2 ** max(job.retry_attempt for job in jobs), 900)
                + self._jitter_seconds()
            )
            await self._async_publish_error(
                jobs, ProviderOutcome.ERROR, None, "temporary error"
            )
        except ProviderFormatError:
            await self._async_publish_error(
                jobs, ProviderOutcome.ERROR, None, "format error"
            )
        finally:
            for job in jobs:
                self._running.remove(job.key)
                self._pending.pop(job.key, None)
            if retry_at is not None:
                self._async_requeue(jobs, retry_at, increment_attempt=True)

    async def _async_publish_error(
        self,
        jobs: list[_DueJob],
        outcome: ProviderOutcome,
        retry_after_seconds: int | None,
        error: str,
    ) -> None:
        """Publish bounded provider state without a raw exception or response body."""
        results = tuple(
            ProviderResult(
                job.plate.identifier,
                job.key[1],
                self._now(),
                outcome,
                retry_after_seconds=retry_after_seconds,
                error=error,
            )
            for job in jobs
        )
        callback_result = self._result_listener(results)
        if callback_result is not None:
            await callback_result

    def _async_requeue(
        self, jobs: list[_DueJob], due_at: datetime, *, increment_attempt: bool = False
    ) -> None:
        """Replace processed jobs with one later eligible job per plate-provider key."""
        for job in jobs:
            self._pending.pop(job.key, None)
            self._enqueue(
                job.key,
                job.plate,
                due_at,
                retry_attempt=job.retry_attempt + int(increment_attempt),
            )

    def _enqueue(
        self, key: JobKey, plate: Plate, due_at: datetime, retry_attempt: int = 0
    ) -> None:
        """Replace a queued due time with one heap entry while retaining its key."""
        job = _DueJob(due_at, next(self._sequence), key, plate, retry_attempt)
        self._pending[key] = job
        heapq.heappush(self._queue, job)
        self._wake.set()

    async def _async_loop(self) -> None:
        """Sleep only until the next due job or an earlier scheduling change."""
        while True:
            await self.async_run_due()
            if not self._queue:
                self._wake.clear()
                await self._wake.wait()
                continue
            delay = max(0, (self._queue[0].due_at - self._now()).total_seconds())
            self._wake.clear()
            with suppress(TimeoutError):
                await asyncio.wait_for(self._wake.wait(), timeout=delay)
