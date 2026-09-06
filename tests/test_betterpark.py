"""Fixture-based BetterPark normalization tests."""

import json
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path

import pytest

from custom_components.park_snoop.models import ProviderOutcome, SessionConfidence
from custom_components.park_snoop.providers.base import (
    ProviderFormatError,
    ProviderRateLimitError,
)
from custom_components.park_snoop.providers.betterpark import BetterParkProvider

FIXTURES = Path(__file__).parent / "fixtures"
CHECKED_AT = datetime(2026, 9, 6, tzinfo=UTC)
RETRY_AFTER_SECONDS = 90


def test_normalizes_active_process_fixture() -> None:
    """An active BetterPark process becomes a normalized active session."""
    payload = json.loads((FIXTURES / "betterpark_active.json").read_text())

    result = BetterParkProvider.normalize_response(
        "BAB123", HTTPStatus.OK, payload, CHECKED_AT
    )

    assert result.outcome is ProviderOutcome.SUCCESS  # noqa: S101
    assert result.sessions[0].confidence is SessionConfidence.CONFIRMED  # noqa: S101
    assert result.sessions[0].fee is not None  # noqa: S101


def test_normalizes_empty_process_list() -> None:
    """An empty response explicitly means no parking at BetterPark."""
    result = BetterParkProvider.normalize_response(
        "BAB123", HTTPStatus.OK, [], CHECKED_AT
    )

    assert result.outcome is ProviderOutcome.NO_PARKING  # noqa: S101


def test_rejects_malformed_process_response() -> None:
    """Unexpected payloads do not leak into normalized state."""
    with pytest.raises(ProviderFormatError):
        BetterParkProvider.normalize_response(
            "BAB123", HTTPStatus.OK, {"id": "missing-list"}, CHECKED_AT
        )


def test_surfaces_rate_limit_retry_time() -> None:
    """A rate-limited response preserves only a scheduler-safe retry delay."""
    with pytest.raises(ProviderRateLimitError) as error:
        BetterParkProvider.normalize_response(
            "BAB123",
            HTTPStatus.TOO_MANY_REQUESTS,
            [],
            CHECKED_AT,
            RETRY_AFTER_SECONDS,
        )

    assert error.value.retry_after_seconds == RETRY_AFTER_SECONDS  # noqa: S101
