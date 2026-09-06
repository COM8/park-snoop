"""Small explicit registry for enabled provider implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Provider


class DuplicateProviderError(ValueError):
    """Raised when a provider identifier is registered more than once."""


class ProviderRegistry:
    """Own enabled provider instances while rejecting ambiguous identifiers."""

    def __init__(self) -> None:
        """Create an empty registry; integration startup registers built-ins."""
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        """Register an adapter once, preventing silent provider replacement."""
        identifier = provider.metadata.identifier
        if identifier in self._providers:
            raise DuplicateProviderError(identifier)
        self._providers[identifier] = provider

    def get(self, identifier: str) -> Provider:
        """Return a provider by its configuration-safe identifier."""
        return self._providers[identifier]

    @property
    def identifiers(self) -> tuple[str, ...]:
        """Return enabled provider identifiers in registration order."""
        return tuple(self._providers)
