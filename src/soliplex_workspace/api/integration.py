"""Integration helpers for wiring workspace into a FastAPI app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI

from soliplex_workspace.api.error_handlers import register_error_handlers
from soliplex_workspace.api.router import router
from soliplex_workspace.providers.disabled import DisabledWorkspaceProvider
from soliplex_workspace.providers.dufs import DufsWorkspaceProvider
from soliplex_workspace.providers.mock import MockWorkspaceProvider

if TYPE_CHECKING:
    from soliplex_workspace.protocol import WorkspaceProvider


def create_workspace_provider(
    config: dict[str, object],
) -> WorkspaceProvider:
    """Factory: config dict -> provider instance.

    Config keys:
        backend: "mock" | "dufs" | "disabled" (default: "disabled")
        dufs_url: base URL for dufs (required if backend="dufs")
    """
    backend = str(config.get("backend", "disabled"))
    if backend == "mock":
        return MockWorkspaceProvider()
    if backend == "dufs":
        url = str(config.get("dufs_url", "http://localhost:5000"))
        return DufsWorkspaceProvider(url)
    return DisabledWorkspaceProvider()


def mount_workspace_api(
    app: FastAPI,
    provider: WorkspaceProvider,
) -> None:
    """Wire workspace provider + routes into a FastAPI app."""
    app.state.workspace_provider = provider
    app.include_router(router)
    register_error_handlers(app)

    async def _close_provider() -> None:
        if hasattr(provider, "close"):
            await provider.close()  # type: ignore[union-attr]

    app.router.on_shutdown.append(_close_provider)
