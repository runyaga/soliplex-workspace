"""E2E test fixtures: FastAPI app + DufsWorkspaceProvider + dufs."""

from __future__ import annotations

import uuid

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from soliplex_workspace.api.integration import mount_workspace_api
from soliplex_workspace.providers.dufs import DufsWorkspaceProvider

DUFS_BASE_URL = "http://localhost:5001"


def is_dufs_available() -> bool:
    """Check if dufs is reachable at localhost:5001."""
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


@pytest.fixture(scope="module")
def e2e_client():
    """FastAPI TestClient with DufsWorkspaceProvider backend.

    mount_workspace_api registers an on_shutdown hook that closes the
    provider's httpx client, so TestClient.__exit__ handles cleanup.
    """
    app = FastAPI()
    provider = DufsWorkspaceProvider(DUFS_BASE_URL)
    mount_workspace_api(app, provider)
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def dufs_provider():
    """DufsWorkspaceProvider connected to local dufs instance."""
    client = httpx.AsyncClient(timeout=30.0)
    provider = DufsWorkspaceProvider(DUFS_BASE_URL, client=client)
    yield provider
    await client.aclose()


@pytest.fixture
async def dufs_workspace(dufs_provider):
    """Create a temporary workspace, yield it, then clean up."""
    room_id = f"test-{uuid.uuid4().hex[:8]}"
    info = await dufs_provider.create_workspace(room_id, "Test Room")
    yield dufs_provider, room_id, info
    await dufs_provider.delete_workspace(room_id)
