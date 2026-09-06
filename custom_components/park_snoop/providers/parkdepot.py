"""ParkDepot/Wemolino's public batched open-orders adapter."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from custom_components.park_snoop.models import (
    Fee,
    FeeMeaning,
    ParkingSession,
    ProviderOutcome,
    ProviderResult,
    SessionConfidence,
    normalize_plate,
)

from .base import (
    NoRateLimitPolicy,
    Provider,
    ProviderFormatError,
    ProviderMetadata,
    ProviderRateLimitError,
)

if TYPE_CHECKING:
    import aiohttp


OPEN_ORDERS_QUERY = """
query GetOpenOrders($plates: [String!]!) {
  b2c_get_open_orders(plates: $plates) {
    orders {
      order {
        order_id
        plate
        status
        start_date
        end_date
      }
      lot {
        lot_id
        name
        address
      }
      price {
        parking_price
        discounted_parking_price
        currency
      }
    }
  }
}
""".strip()

OPEN_ORDERS_URL = "https://hasura.prod.park-depot.de/v1/graphql"


class ParkDepotProvider(Provider):
    """Read-only adapter for ParkDepot/Wemolino's open-orders GraphQL query."""

    metadata = ProviderMetadata(
        identifier="parkdepot", name="ParkDepot/Wemolino", supports_batching=True
    )

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Use Home Assistant's shared HTTP session for controlled requests."""
        self._session = session
        self.rate_limit_policy = NoRateLimitPolicy()

    @staticmethod
    def normalize_response(
        plates: tuple[str, ...],
        status: int,
        payload: Any,
        checked_at: datetime,
        retry_after_seconds: int | None = None,
    ) -> tuple[ProviderResult, ...]:
        """Convert a saved GraphQL response into one result for each requested plate."""
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            raise ProviderRateLimitError(retry_after_seconds)
        if status != HTTPStatus.OK or not isinstance(payload, dict):
            raise ProviderFormatError
        if payload.get("errors"):
            raise ProviderFormatError

        data = payload.get("data")
        if not isinstance(data, dict):
            raise ProviderFormatError
        open_orders = data.get("b2c_get_open_orders")
        if not isinstance(open_orders, dict):
            raise ProviderFormatError
        orders = open_orders.get("orders")
        if not isinstance(orders, list):
            raise ProviderFormatError

        sessions_by_plate: dict[str, list[ParkingSession]] = {
            plate: [] for plate in plates
        }
        for item in orders:
            plate, session = _normalize_order(item)
            if plate not in sessions_by_plate:
                raise ProviderFormatError
            sessions_by_plate[plate].append(session)

        return tuple(
            ProviderResult(
                plate,
                "parkdepot",
                checked_at,
                ProviderOutcome.SUCCESS if sessions else ProviderOutcome.NO_PARKING,
                tuple(sessions),
            )
            for plate, sessions in sessions_by_plate.items()
        )

    async def async_query(self, plates: tuple[str, ...]) -> tuple[ProviderResult, ...]:
        """Query all compatible plates together through the public GraphQL endpoint."""
        payload = {"query": OPEN_ORDERS_QUERY, "variables": {"plates": list(plates)}}
        headers = {"X-Contact-Info": "Home Assistant Park Snoop"}
        async with self._session.post(
            OPEN_ORDERS_URL, json=payload, headers=headers
        ) as response:
            retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
            response_payload = await response.json(content_type=None)
            return self.normalize_response(
                plates,
                response.status,
                response_payload,
                datetime.now().astimezone(),
                retry_after,
            )


def _normalize_order(item: Any) -> tuple[str, ParkingSession]:
    """Normalize one nested GraphQL order without retaining the raw response."""
    if not isinstance(item, dict):
        raise ProviderFormatError
    order = item.get("order")
    if not isinstance(order, dict):
        raise ProviderFormatError
    raw_plate = order.get("plate")
    order_id = order.get("order_id")
    if not isinstance(raw_plate, str) or not isinstance(order_id, str):
        raise ProviderFormatError

    lot = item.get("lot")
    location = lot.get("name") if isinstance(lot, dict) else None
    return normalize_plate(raw_plate), ParkingSession(
        "parkdepot",
        order_id,
        SessionConfidence.CONFIRMED,
        _parse_timestamp(order.get("start_date")),
        _parse_timestamp(order.get("end_date")),
        location if isinstance(location, str) else None,
        _parse_fee(item.get("price")),
    )


def _parse_fee(value: Any) -> Fee | None:
    """Use the visible parking price as a current amount due when supplied."""
    if not isinstance(value, dict) or not isinstance(value.get("currency"), str):
        return None
    raw_amount = value.get("discounted_parking_price")
    if raw_amount is None:
        raw_amount = value.get("parking_price")
    if raw_amount is None:
        return None
    try:
        return Fee(Decimal(str(raw_amount)), value["currency"], FeeMeaning.AMOUNT_DUE)
    except ArithmeticError:
        raise ProviderFormatError from None


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse an ISO timestamp while treating absent values as unavailable."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _retry_after_seconds(value: str | None) -> int | None:
    """Parse a numeric Retry-After header; date forms are handled by the scheduler."""
    try:
        return max(0, int(value)) if value is not None else None
    except ValueError:
        return None
