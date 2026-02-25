"""Unit tests for tools.bridge — signature preservation + binding."""

from __future__ import annotations

import inspect
import json

import pytest

from soliplex_workspace.providers.mock import MockWorkspaceProvider
from soliplex_workspace.tools.bridge import _bind_tool
from soliplex_workspace.tools.bridge import make_workspace_tools
from soliplex_workspace.tools.core import workspace_list
from soliplex_workspace.tools.core import workspace_read
from soliplex_workspace.tools.core import workspace_write


@pytest.fixture
async def _workspace(mock_provider: MockWorkspaceProvider):
    """Create a workspace for the test room."""
    await mock_provider.create_workspace("room-1", "Test Room")
    return mock_provider


class TestBindToolSignature:
    """_bind_tool preserves signature minus provider/room_id."""

    def test_removes_provider_and_room_id(self):
        provider = MockWorkspaceProvider()
        bound = _bind_tool(workspace_list, provider, "room-1")
        sig = inspect.signature(bound)
        param_names = list(sig.parameters.keys())
        assert "provider" not in param_names
        assert "room_id" not in param_names

    def test_preserves_remaining_params(self):
        provider = MockWorkspaceProvider()
        bound = _bind_tool(workspace_list, provider, "room-1")
        sig = inspect.signature(bound)
        param_names = list(sig.parameters.keys())
        assert "path" in param_names
        assert "recursive" in param_names
        assert "max_depth" in param_names
        assert "max_results" in param_names

    def test_preserves_defaults(self):
        provider = MockWorkspaceProvider()
        bound = _bind_tool(workspace_list, provider, "room-1")
        sig = inspect.signature(bound)
        assert sig.parameters["path"].default == "/"
        assert sig.parameters["recursive"].default is False

    def test_preserves_return_annotation(self):
        provider = MockWorkspaceProvider()
        bound = _bind_tool(workspace_list, provider, "room-1")
        sig = inspect.signature(bound)
        assert sig.return_annotation is not inspect.Parameter.empty


class TestBindToolMetadata:
    """_bind_tool preserves __doc__, __name__, etc."""

    def test_preserves_docstring(self):
        provider = MockWorkspaceProvider()
        bound = _bind_tool(workspace_read, provider, "room-1")
        assert bound.__doc__ is not None
        assert "Read the text content" in bound.__doc__

    def test_preserves_name(self):
        provider = MockWorkspaceProvider()
        bound = _bind_tool(workspace_read, provider, "room-1")
        assert bound.__name__ == "workspace_read"

    def test_preserves_module(self):
        provider = MockWorkspaceProvider()
        bound = _bind_tool(workspace_read, provider, "room-1")
        assert bound.__module__ == workspace_read.__module__

    def test_annotations_exclude_provider_room_id(self):
        provider = MockWorkspaceProvider()
        bound = _bind_tool(workspace_write, provider, "room-1")
        assert "provider" not in bound.__annotations__
        assert "room_id" not in bound.__annotations__
        assert "return" in bound.__annotations__


class TestMakeWorkspaceTools:
    """make_workspace_tools returns all 9 tools."""

    def test_returns_nine_tools(self):
        provider = MockWorkspaceProvider()
        tools = make_workspace_tools(provider, "room-1")
        assert len(tools) == 9

    def test_tool_names(self):
        provider = MockWorkspaceProvider()
        tools = make_workspace_tools(provider, "room-1")
        names = {t.__name__ for t in tools}
        expected = {
            "workspace_list",
            "workspace_read",
            "workspace_write",
            "workspace_info",
            "workspace_find",
            "workspace_mkdir",
            "workspace_move",
            "workspace_delete",
            "workspace_copy",
        }
        assert names == expected

    def test_all_have_docstrings(self):
        provider = MockWorkspaceProvider()
        tools = make_workspace_tools(provider, "room-1")
        for tool in tools:
            assert tool.__doc__ is not None, (
                f"{tool.__name__} missing docstring"
            )

    def test_all_signatures_lack_provider_room_id(self):
        provider = MockWorkspaceProvider()
        tools = make_workspace_tools(provider, "room-1")
        for tool in tools:
            sig = inspect.signature(tool)
            param_names = list(sig.parameters.keys())
            assert "provider" not in param_names, tool.__name__
            assert "room_id" not in param_names, tool.__name__


@pytest.mark.usefixtures("_workspace")
class TestBoundToolExecution:
    """Bound tools actually call the provider correctly."""

    async def test_list_empty_workspace(
        self,
        mock_provider: MockWorkspaceProvider,
    ):
        tools = make_workspace_tools(mock_provider, "room-1")
        list_tool = next(t for t in tools if t.__name__ == "workspace_list")
        result = json.loads(await list_tool(path="/"))
        assert result["path"] == "/"
        assert result["files"] == []

    async def test_write_and_read(
        self,
        mock_provider: MockWorkspaceProvider,
    ):
        tools = make_workspace_tools(mock_provider, "room-1")
        write_tool = next(t for t in tools if t.__name__ == "workspace_write")
        read_tool = next(t for t in tools if t.__name__ == "workspace_read")
        await write_tool(path="/hello.txt", content="Hello!")
        result = json.loads(await read_tool(path="/hello.txt"))
        assert result["content"] == "Hello!"

    async def test_mkdir_and_list(
        self,
        mock_provider: MockWorkspaceProvider,
    ):
        tools = make_workspace_tools(mock_provider, "room-1")
        mkdir_tool = next(t for t in tools if t.__name__ == "workspace_mkdir")
        list_tool = next(t for t in tools if t.__name__ == "workspace_list")
        await mkdir_tool(path="/docs")
        result = json.loads(await list_tool(path="/"))
        names = [f["name"] for f in result["files"]]
        assert "docs" in names


class TestAutoCreateWorkspace:
    """auto_create flag triggers lazy workspace creation."""

    async def test_auto_create_workspace_on_first_call(self):
        provider = MockWorkspaceProvider()
        tools = make_workspace_tools(provider, "room-auto")
        list_tool = next(t for t in tools if t.__name__ == "workspace_list")
        # No workspace pre-created — auto_create should handle it
        result = json.loads(await list_tool(path="/"))
        assert result["path"] == "/"
        ws = await provider.get_workspace("room-auto")
        assert ws is not None
        assert ws.room_id == "room-auto"

    async def test_auto_create_only_called_once(self):
        provider = MockWorkspaceProvider()
        tools = make_workspace_tools(provider, "room-once")
        list_tool = next(t for t in tools if t.__name__ == "workspace_list")
        await list_tool(path="/")
        # Second call should skip ensure (workspace already exists)
        await list_tool(path="/")
        ws = await provider.get_workspace("room-once")
        assert ws is not None

    async def test_auto_create_disabled(self):
        from soliplex_workspace.exceptions import WorkspaceNotFoundError

        provider = MockWorkspaceProvider()
        tools = make_workspace_tools(
            provider, "room-no-auto", auto_create=False
        )
        list_tool = next(t for t in tools if t.__name__ == "workspace_list")
        with pytest.raises(WorkspaceNotFoundError):
            await list_tool(path="/")

    async def test_idempotent_create_workspace(self):
        provider = MockWorkspaceProvider()
        first = await provider.create_workspace("room-idem", "Room")
        second = await provider.create_workspace("room-idem", "Room")
        assert first.room_id == second.room_id
