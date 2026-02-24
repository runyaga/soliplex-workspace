"""Disabled workspace provider -- raises on every operation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from soliplex_workspace.exceptions import WorkspaceDisabledError

if TYPE_CHECKING:
    from soliplex_workspace.models import FileInfo
    from soliplex_workspace.models import WorkspaceInfo


class DisabledWorkspaceProvider:
    """No-op provider that raises on every method.

    Used when workspace feature is turned off in the Soliplex
    installation configuration.
    """

    async def create_workspace(
        self,
        room_id: str,  # noqa: ARG002
        name: str,  # noqa: ARG002
        quota_bytes: int | None = None,  # noqa: ARG002
    ) -> WorkspaceInfo:
        raise WorkspaceDisabledError

    async def delete_workspace(
        self,
        room_id: str,  # noqa: ARG002
    ) -> None:
        raise WorkspaceDisabledError

    async def get_workspace(
        self,
        room_id: str,  # noqa: ARG002
    ) -> WorkspaceInfo | None:
        raise WorkspaceDisabledError

    async def get_file_info(
        self,
        room_id: str,  # noqa: ARG002
        path: str,  # noqa: ARG002
    ) -> FileInfo:
        raise WorkspaceDisabledError

    async def list_files(
        self,
        room_id: str,  # noqa: ARG002
        path: str = "/",  # noqa: ARG002
    ) -> list[FileInfo]:
        raise WorkspaceDisabledError

    async def upload_file(
        self,
        room_id: str,  # noqa: ARG002
        path: str,  # noqa: ARG002
        content: bytes,  # noqa: ARG002
    ) -> FileInfo:
        raise WorkspaceDisabledError

    async def download_file(
        self,
        room_id: str,  # noqa: ARG002
        path: str,  # noqa: ARG002
    ) -> bytes:
        raise WorkspaceDisabledError

    async def delete_file(
        self,
        room_id: str,  # noqa: ARG002
        path: str,  # noqa: ARG002
    ) -> None:
        raise WorkspaceDisabledError

    async def create_folder(
        self,
        room_id: str,  # noqa: ARG002
        path: str,  # noqa: ARG002
    ) -> FileInfo:
        raise WorkspaceDisabledError

    async def move(
        self,
        room_id: str,  # noqa: ARG002
        src: str,  # noqa: ARG002
        dst: str,  # noqa: ARG002
    ) -> FileInfo:
        raise WorkspaceDisabledError

    async def get_web_ui_url(
        self,
        room_id: str,  # noqa: ARG002
    ) -> str | None:
        raise WorkspaceDisabledError

    async def get_webdav_url(
        self,
        room_id: str,  # noqa: ARG002
    ) -> str | None:
        raise WorkspaceDisabledError
