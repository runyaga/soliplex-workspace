"""Shared fixtures for use case scenario tests."""

from __future__ import annotations

import uuid

import httpx
import pytest

from soliplex_workspace.providers.dufs import DufsWorkspaceProvider

DUFS_BASE_URL = "http://localhost:5001"


def is_dufs_available() -> bool:
    try:
        r = httpx.get(DUFS_BASE_URL, timeout=2.0)
    except httpx.ConnectError:
        return False
    else:
        return r.status_code == 200


requires_dufs = pytest.mark.skipif(
    not is_dufs_available(),
    reason="dufs not available at localhost:5001",
)


@pytest.fixture
async def workspace():
    """Create a temp workspace, yield (provider, room_id), cleanup."""
    client = httpx.AsyncClient(timeout=30.0)
    provider = DufsWorkspaceProvider(DUFS_BASE_URL, client=client)
    room_id = f"uc-{uuid.uuid4().hex[:8]}"
    await provider.create_workspace(room_id, "UC Test")
    yield provider, room_id
    await provider.delete_workspace(room_id)
    await client.aclose()
