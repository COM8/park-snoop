"""Shared pytest fixtures for Park Snoop."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load this repository's custom integration."""
