"""Integration tests for lazy workspace creation against real dufs."""

from __future__ import annotations

import uuid

import pytest

from soliplex_workspace.exceptions import WorkspaceNotFoundError
from soliplex_workspace.tools.bridge import make_workspace_tools

from .conftest import requires_dufs

pytestmark = [requires_dufs, pytest.mark.dufs]


class TestLazyCreationDufs:
    async def test_auto_create_on_first_tool_call(self, dufs_provider):
        """Bound tool with auto_create=True creates workspace on dufs."""
        room_id = f"test-lazy-{uuid.uuid4().hex[:8]}"
        tools = make_workspace_tools(dufs_provider, room_id, auto_create=True)
        list_tool = next(t for t in tools if t.__name__ == "workspace_list")

        try:
            await list_tool(path="/")

            ws = await dufs_provider.get_workspace(room_id)
            assert ws is not None
            assert ws.room_id == room_id
        finally:
            await dufs_provider.delete_workspace(room_id)

    async def test_auto_create_idempotent_dufs(self, dufs_provider):
        """auto_create on existing workspace is a no-op."""
        room_id = f"test-lazy-{uuid.uuid4().hex[:8]}"
        await dufs_provider.create_workspace(room_id, "Pre-created")
        await dufs_provider.upload_file(room_id, "/existing.txt", b"data")

        tools = make_workspace_tools(dufs_provider, room_id, auto_create=True)
        list_tool = next(t for t in tools if t.__name__ == "workspace_list")

        try:
            await list_tool(path="/")

            data = await dufs_provider.download_file(room_id, "/existing.txt")
            assert data == b"data"
        finally:
            await dufs_provider.delete_workspace(room_id)

    async def test_auto_create_disabled_dufs(self, dufs_provider):
        """auto_create=False raises on non-existent workspace."""
        room_id = f"test-lazy-{uuid.uuid4().hex[:8]}"
        tools = make_workspace_tools(dufs_provider, room_id, auto_create=False)
        list_tool = next(t for t in tools if t.__name__ == "workspace_list")

        with pytest.raises(WorkspaceNotFoundError):
            await list_tool(path="/")
