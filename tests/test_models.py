"""Tests for normalized parking models and plate aggregation."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from custom_components.park_snoop.models import (
    Fee,
    FeeMeaning,
    ParkingSession,
    Plate,
    SessionConfidence,
    aggregate_sessions,
    plate_unique_id,
)


def _session(
    provider_id: str,
    session_id: str,
    confidence: SessionConfidence = SessionConfidence.CONFIRMED,
    fee: Fee | None = None,
) -> ParkingSession:
    """Build a normalized active session for aggregation tests."""
    return ParkingSession(
        provider_id=provider_id,
        provider_session_id=session_id,
        confidence=confidence,
        started_at=datetime(2026, 9, 6, tzinfo=UTC),
        fee=fee,
    )


def test_aggregate_marks_concurrent_sessions_as_multiple() -> None:
    """Concurrent provider records remain visible instead of being collapsed."""
    aggregate = aggregate_sessions(
        [_session("betterpark", "one"), _session("parkdepot", "two")]
    )

    assert aggregate.status == "multiple_sessions"  # noqa: S101
    assert aggregate.active_session_count == len(aggregate.sessions)  # noqa: S101


def test_aggregate_marks_unknown_fees_incomplete() -> None:
    """A missing fee never becomes an invented monetary total."""
    aggregate = aggregate_sessions([_session("betterpark", "one")])

    assert aggregate.fee_totals == {}  # noqa: S101
    assert not aggregate.fees_complete  # noqa: S101


def test_aggregate_keeps_mixed_currency_totals_separate() -> None:
    """EUR and USD fees remain separate, never converted or summed together."""
    aggregate = aggregate_sessions(
        [
            _session(
                "betterpark",
                "one",
                fee=Fee(Decimal("2.50"), "EUR", FeeMeaning.ACCRUED_ESTIMATE),
            ),
            _session(
                "parkdepot",
                "two",
                fee=Fee(Decimal("3.00"), "USD", FeeMeaning.AMOUNT_DUE),
            ),
        ]
    )

    assert aggregate.fee_totals == {"EUR": Decimal("2.50"), "USD": Decimal("3.00")}  # noqa: S101
    assert aggregate.fees_complete  # noqa: S101


def test_plate_unique_id_is_stable_when_display_name_changes() -> None:
    """Changing UI metadata cannot orphan a plate's entity history."""
    initial = Plate(identifier="BAB123", display_name="Car")
    renamed = replace(initial, display_name="Family car")

    assert plate_unique_id(initial.identifier) == plate_unique_id(renamed.identifier)  # noqa: S101
