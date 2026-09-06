"""Fixture-based ParkDepot/Wemolino normalization tests."""

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
from custom_components.park_snoop.providers.parkdepot import ParkDepotProvider

FIXTURES = Path(__file__).parent / "fixtures"
CHECKED_AT = datetime(2026, 9, 6, tzinfo=UTC)
PLATES = ("BAB123", "MUC456")
RETRY_AFTER_SECONDS = 90


def test_normalizes_batched_open_order_fixture() -> None:
    """One GraphQL response produces a result for every requested plate."""
    payload = json.loads((FIXTURES / "parkdepot_open_orders.json").read_text())

    results = ParkDepotProvider.normalize_response(
        PLATES, HTTPStatus.OK, payload, CHECKED_AT
    )

    by_plate = {result.plate: result for result in results}
    assert by_plate["BAB123"].outcome is ProviderOutcome.SUCCESS  # noqa: S101
    assert by_plate["MUC456"].outcome is ProviderOutcome.NO_PARKING  # noqa: S101
    session = by_plate["BAB123"].sessions[0]
    assert session.confidence is SessionConfidence.CONFIRMED  # noqa: S101
    assert session.fee is not None  # noqa: S101


def test_normalizes_empty_open_orders() -> None:
    """Empty open orders explicitly mean no parking for every batched plate."""
    payload = {"data": {"b2c_get_open_orders": {"orders": []}}}

    results = ParkDepotProvider.normalize_response(
        PLATES, HTTPStatus.OK, payload, CHECKED_AT
    )

    assert all(result.outcome is ProviderOutcome.NO_PARKING for result in results)  # noqa: S101


def test_rejects_graphql_errors() -> None:
    """GraphQL errors are never exposed as a successful parking result."""
    payload = {"errors": [{"message": "request rejected"}]}

    with pytest.raises(ProviderFormatError):
        ParkDepotProvider.normalize_response(PLATES, HTTPStatus.OK, payload, CHECKED_AT)


def test_surfaces_rate_limit_retry_time() -> None:
    """A rate-limited batch keeps only the scheduler-safe retry delay."""
    with pytest.raises(ProviderRateLimitError) as error:
        ParkDepotProvider.normalize_response(
            PLATES,
            HTTPStatus.TOO_MANY_REQUESTS,
            {},
            CHECKED_AT,
            RETRY_AFTER_SECONDS,
        )

    assert error.value.retry_after_seconds == RETRY_AFTER_SECONDS  # noqa: S101
