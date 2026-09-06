"""Provider-neutral, immutable parking monitoring models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


class FeeMeaning(StrEnum):
    """Explain what a provider-supplied monetary value represents."""

    ACCRUED_ESTIMATE = "accrued_estimate"
    AMOUNT_DUE = "amount_due"
    FINAL_CHARGE = "final_charge"
    UNKNOWN = "unknown"


class SessionConfidence(StrEnum):
    """Describe how conclusively a provider has established session state."""

    CONFIRMED = "confirmed"
    POSSIBLY_ACTIVE = "possibly_active"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class ProviderOutcome(StrEnum):
    """Summarize one provider query without leaking its raw response."""

    SUCCESS = "success"
    NO_PARKING = "no_parking"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


class ParkingStatus(StrEnum):
    """Automation-friendly aggregate state for a monitored plate."""

    NOT_PARKED = "not_parked"
    PARKING = "parking"
    MULTIPLE_SESSIONS = "multiple_sessions"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Plate:
    """A normalized, user-configured license plate record."""

    identifier: str
    display_name: str | None = None
    notes: str | None = None
    frequency_minutes: int = 5
    provider_ids: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        """Return the user-facing name without changing stable identity."""
        return self.display_name or self.identifier


def normalize_plate(value: str) -> str:
    """Normalize a plate to a stable, whitespace-free uppercase identifier."""
    return re.sub(r"[\s-]+", "", value).upper()


def plate_unique_id(identifier: str) -> str:
    """Return a stable, opaque Home Assistant identifier for a normalized plate."""
    return f"plate_{sha256(identifier.encode()).hexdigest()[:16]}"


@dataclass(frozen=True, slots=True)
class Fee:
    """A known provider fee with currency and semantic meaning."""

    amount: Decimal
    currency: str
    meaning: FeeMeaning


@dataclass(frozen=True, slots=True)
class ParkingSession:
    """A normalized parking record identified within one provider."""

    provider_id: str
    provider_session_id: str | None
    confidence: SessionConfidence
    started_at: datetime | None = None
    ended_at: datetime | None = None
    location: str | None = None
    fee: Fee | None = None

    @property
    def key(self) -> tuple[str, str | None]:
        """Return the stable in-memory key for the provider record."""
        return (self.provider_id, self.provider_session_id)


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """A provider-neutral result for one plate check."""

    plate: str
    provider_id: str
    checked_at: datetime
    outcome: ProviderOutcome
    sessions: tuple[ParkingSession, ...] = ()
    retry_after_seconds: int | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class AggregateState:
    """The bounded, currency-safe state rendered by plate entities."""

    status: ParkingStatus
    active_session_count: int
    sessions: tuple[ParkingSession, ...]
    fee_totals: dict[str, Decimal]
    fees_complete: bool


def aggregate_sessions(sessions: list[ParkingSession]) -> AggregateState:
    """Aggregate active sessions while preserving uncertainty and currencies."""
    active = tuple(
        session
        for session in sessions
        if session.confidence
        in (SessionConfidence.CONFIRMED, SessionConfidence.POSSIBLY_ACTIVE)
    )
    totals: dict[str, Decimal] = {}
    fees_complete = bool(active)
    for session in active:
        if session.fee is None or session.fee.meaning is FeeMeaning.UNKNOWN:
            fees_complete = False
            continue
        currency = session.fee.currency.upper()
        totals[currency] = totals.get(currency, 0) + session.fee.amount

    if len(active) > 1:
        status = ParkingStatus.MULTIPLE_SESSIONS
    elif len(active) == 1 and active[0].confidence is SessionConfidence.POSSIBLY_ACTIVE:
        status = ParkingStatus.UNCERTAIN
    elif len(active) == 1:
        status = ParkingStatus.PARKING
    else:
        status = ParkingStatus.NOT_PARKED

    return AggregateState(status, len(active), active, totals, fees_complete)
