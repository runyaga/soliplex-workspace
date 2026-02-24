"""WorkspaceProvider protocol -- the facade interface."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol
from typing import runtime_checkable

if TYPE_CHECKING:
    from soliplex_workspace.models import FileInfo
    from soliplex_workspace.models import WorkspaceInfo


@runtime_checkable
class WorkspaceProvider(Protocol):
    """Abstract interface for room file workspace backends.

    Implementations must handle all file operations for a given
    room. Each room maps to exactly one workspace. The provider
    is responsible for isolation between rooms.
    """

    async def create_workspace(
        self,
        room_id: str,
        name: str,
        quota_bytes: int | None = None,
    ) -> WorkspaceInfo:
        """Create a new workspace for a room."""
        ...

    async def delete_workspace(self, room_id: str) -> None:
        """Delete a room's workspace and all its files."""
        ...

    async def get_workspace(
        self,
        room_id: str,
    ) -> WorkspaceInfo | None:
        """Get workspace info, or None if it doesn't exist."""
        ...

    async def list_files(
        self,
        room_id: str,
        path: str = "/",
    ) -> list[FileInfo]:
        """List files and folders at the given path."""
        ...

    async def upload_file(
        self,
        room_id: str,
        path: str,
        content: bytes,
    ) -> FileInfo:
        """Upload a file to the workspace."""
        ...

    async def download_file(
        self,
        room_id: str,
        path: str,
    ) -> bytes:
        """Download a file's contents."""
        ...

    async def delete_file(
        self,
        room_id: str,
        path: str,
    ) -> None:
        """Delete a file or empty folder."""
        ...

    async def create_folder(
        self,
        room_id: str,
        path: str,
    ) -> FileInfo:
        """Create a folder in the workspace."""
        ...

    async def move(
        self,
        room_id: str,
        src: str,
        dst: str,
    ) -> FileInfo:
        """Move or rename a file/folder."""
        ...

    async def get_web_ui_url(
        self,
        room_id: str,
    ) -> str | None:
        """URL to a web file browser for this workspace."""
        ...

    async def get_webdav_url(
        self,
        room_id: str,
    ) -> str | None:
        """WebDAV endpoint URL for this workspace."""
        ...
