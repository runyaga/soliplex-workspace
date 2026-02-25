"""E2E: real LLM agent interacting with real dufs.

A pydantic-ai Agent backed by Ollama (gpt-oss:20b on bizon:11434)
drives workspace tools against a real DufsWorkspaceProvider.
These tests require both dufs and the Ollama GPU server to be running.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from soliplex_workspace.tools.bridge import make_workspace_tools

from .conftest import requires_dufs

OLLAMA_BASE_URL = "http://bizon:11434"
MODEL_NAME = "gpt-oss:20b"

SYSTEM_PROMPT = (
    "You are an automated file-management testing agent. "
    "You MUST use the provided workspace tools to complete tasks. "
    "Execute tools immediately without asking for permission. "
    "Never simulate or guess file contents without reading them."
)


def is_ollama_available() -> bool:
    """Check if Ollama is reachable and has the required model."""
    try:
        r = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
    except httpx.ConnectError:
        return False
    else:
        return r.status_code == 200 and MODEL_NAME in r.text


requires_ollama = pytest.mark.skipif(
    not is_ollama_available(),
    reason=f"Ollama with {MODEL_NAME} not available at {OLLAMA_BASE_URL}",
)

pytestmark = [
    requires_dufs,
    requires_ollama,
    pytest.mark.e2e,
    pytest.mark.needs_llm,
]


def _room_id() -> str:
    return f"llm-e2e-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def llm_model():
    """pydantic-ai model for Ollama gpt-oss:20b."""
    provider = OllamaProvider(
        base_url=f"{OLLAMA_BASE_URL}/v1",
        api_key="dummy",
    )
    return OpenAIChatModel(MODEL_NAME, provider=provider)


class TestRealLLMAgentWithDufs:
    """Agent driven by a real LLM against real dufs."""

    async def test_llm_creates_and_reads_file(self, dufs_provider, llm_model):
        """LLM writes a file to dufs and reads it back."""
        room_id = _room_id()
        tools = make_workspace_tools(dufs_provider, room_id)

        agent: Agent[None, str] = Agent(
            llm_model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

        try:
            result = await agent.run(
                "Create a file called /hello.txt with the exact "
                "content 'Hello World'. "
                "Then read the file back to verify. "
                "Reply with VERIFIED if successful."
            )

            assert "VERIFIED" in result.output.upper()

            data = await dufs_provider.download_file(room_id, "/hello.txt")
            assert b"Hello World" in data
        finally:
            await dufs_provider.delete_workspace(room_id)

    async def test_llm_lists_workspace_contents(
        self, dufs_provider, llm_model
    ):
        """LLM lists files after seeding workspace."""
        room_id = _room_id()

        await dufs_provider.create_workspace(room_id, "LLM Test")
        await dufs_provider.upload_file(room_id, "/notes.md", b"# Notes")
        await dufs_provider.upload_file(room_id, "/data.csv", b"a,b\n1,2")

        tools = make_workspace_tools(dufs_provider, room_id)

        agent: Agent[None, str] = Agent(
            llm_model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

        try:
            result = await agent.run(
                "List the files in the workspace root. "
                "Tell me the names of all files you find."
            )

            output = result.output.lower()
            assert "notes" in output
            assert "data" in output
        finally:
            await dufs_provider.delete_workspace(room_id)

    async def test_llm_multi_step_workflow(self, dufs_provider, llm_model):
        """LLM executes a multi-step write, list, read workflow."""
        room_id = _room_id()
        tools = make_workspace_tools(dufs_provider, room_id)

        agent: Agent[None, str] = Agent(
            llm_model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            retries=3,
        )

        try:
            result = await agent.run(
                "1. Create a file /report.md with content "
                "'# Status Report\\nAll systems operational.'\n"
                "2. List the workspace root to confirm the file exists.\n"
                "3. Read /report.md back.\n"
                "4. Reply with COMPLETE and the file contents."
            )

            assert "COMPLETE" in result.output.upper()

            data = await dufs_provider.download_file(room_id, "/report.md")
            assert b"Status Report" in data
        finally:
            await dufs_provider.delete_workspace(room_id)
