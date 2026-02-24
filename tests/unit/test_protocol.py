"""Tests for WorkspaceProvider protocol compliance."""

from soliplex_workspace.protocol import WorkspaceProvider
from soliplex_workspace.providers.disabled import DisabledWorkspaceProvider
from soliplex_workspace.providers.mock import MockWorkspaceProvider


class TestProtocolCompliance:
    """Verify providers satisfy the WorkspaceProvider protocol."""

    def test_mock_is_workspace_provider(self):
        provider = MockWorkspaceProvider()
        assert isinstance(provider, WorkspaceProvider)

    def test_disabled_is_workspace_provider(self):
        provider = DisabledWorkspaceProvider()
        assert isinstance(provider, WorkspaceProvider)
