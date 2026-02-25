"""FastAPI dependency injection for workspace provider."""

from __future__ import annotations

from typing import Any

from fastapi import Request

PROVIDER_STATE_KEY = "workspace_provider"


async def depend_the_workspace_provider(
    request: Request,
) -> Any:
    """Extract the workspace provider from app state."""
    return request.app.state.workspace_provider
