"""Shared test fixtures."""

import pytest

from soliplex_workspace.providers.disabled import DisabledWorkspaceProvider
from soliplex_workspace.providers.mock import MockWorkspaceProvider


@pytest.fixture
def mock_provider():
    """Fresh MockWorkspaceProvider for each test."""
    return MockWorkspaceProvider()


@pytest.fixture
def disabled_provider():
    """DisabledWorkspaceProvider instance."""
    return DisabledWorkspaceProvider()
