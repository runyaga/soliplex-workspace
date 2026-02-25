"""E2E: agent tool calling against real dufs via FunctionModel.

pydantic-ai Agent with workspace tools bound to a real
DufsWorkspaceProvider — no LLM API key required, but dufs must
be running at localhost:5001.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic_ai import Agent
from pydantic_ai import ModelMessage
from pydantic_ai import ModelResponse
from pydantic_ai import TextPart
from pydantic_ai import ToolCallPart
from pydantic_ai.models.function import AgentInfo
from pydantic_ai.models.function import FunctionModel

from soliplex_workspace.tools.bridge import make_workspace_tools

from .conftest import requires_dufs

pytestmark = [requires_dufs, pytest.mark.e2e]


def _room_id() -> str:
    return f"agent-dufs-{uuid.uuid4().hex[:8]}"


# -- Deterministic model functions ---------------------------------


def _write_then_read_model(
    messages: list[ModelMessage],
    info: AgentInfo,  # noqa: ARG001
) -> ModelResponse:
    """Write a file then read it back."""
    tool_returns = [
        p for m in messages for p in m.parts if p.part_kind == "tool-return"
    ]
    step = len(tool_returns)

    if step == 0:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "workspace_write",
                    {
                        "path": "/hello.txt",
                        "content": "Hello from dufs agent!",
                    },
                )
            ]
        )
    if step == 1:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "workspace_read",
                    {"path": "/hello.txt"},
                )
            ]
        )
    return ModelResponse(
        parts=[TextPart("File written and verified on dufs.")]
    )


def _lazy_list_model(
    messages: list[ModelMessage],
    info: AgentInfo,  # noqa: ARG001
) -> ModelResponse:
    """List workspace — should trigger lazy creation."""
    tool_returns = [
        p for m in messages for p in m.parts if p.part_kind == "tool-return"
    ]
    if len(tool_returns) == 0:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "workspace_list",
                    {"path": "/"},
                )
            ]
        )
    return ModelResponse(
        parts=[TextPart("Workspace was lazily created on dufs.")]
    )


def _three_tool_model(
    messages: list[ModelMessage],
    info: AgentInfo,  # noqa: ARG001
) -> ModelResponse:
    """list -> write -> read sequence against dufs."""
    tool_returns = [
        p for m in messages for p in m.parts if p.part_kind == "tool-return"
    ]
    step = len(tool_returns)

    if step == 0:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "workspace_list",
                    {"path": "/", "recursive": True},
                )
            ]
        )
    if step == 1:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "workspace_write",
                    {
                        "path": "/notes.md",
                        "content": "# Notes\nFrom three-tool test.",
                    },
                )
            ]
        )
    if step == 2:
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "workspace_read",
                    {"path": "/notes.md"},
                )
            ]
        )
    return ModelResponse(
        parts=[TextPart("Three-tool sequence complete on dufs.")]
    )


# -- Tests ---------------------------------------------------------


class TestAgentWithDufs:
    """Agent drives workspace tools against real dufs."""

    async def test_agent_writes_to_dufs(self, dufs_provider):
        """Agent writes a file and reads it back via real dufs."""
        room_id = _room_id()
        tools = make_workspace_tools(dufs_provider, room_id)

        agent: Agent[None, str] = Agent(
            FunctionModel(_write_then_read_model),
            tools=tools,
        )

        try:
            result = await agent.run("Write and read on dufs")
            assert "verified" in result.output.lower()

            data = await dufs_provider.download_file(room_id, "/hello.txt")
            assert data == b"Hello from dufs agent!"
        finally:
            await dufs_provider.delete_workspace(room_id)

    async def test_agent_lazy_creation_dufs(self, dufs_provider):
        """Workspace auto-created on first tool call against dufs."""
        room_id = _room_id()
        tools = make_workspace_tools(dufs_provider, room_id)

        agent: Agent[None, str] = Agent(
            FunctionModel(_lazy_list_model),
            tools=tools,
        )

        try:
            result = await agent.run("List a non-existent workspace")
            assert "lazily" in result.output.lower()

            ws = await dufs_provider.get_workspace(room_id)
            assert ws is not None
        finally:
            await dufs_provider.delete_workspace(room_id)

    async def test_agent_three_tool_sequence_dufs(self, dufs_provider):
        """list -> write -> read all work against real dufs."""
        room_id = _room_id()
        tools = make_workspace_tools(dufs_provider, room_id)

        agent: Agent[None, str] = Agent(
            FunctionModel(_three_tool_model),
            tools=tools,
        )

        try:
            result = await agent.run("Run three tools on dufs")
            assert "complete" in result.output.lower()

            data = await dufs_provider.download_file(room_id, "/notes.md")
            assert b"# Notes" in data
        finally:
            await dufs_provider.delete_workspace(room_id)
