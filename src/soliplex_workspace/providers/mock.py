"""In-memory mock workspace provider for testing."""

from __future__ import annotations

import posixpath

from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.exceptions import WorkspaceNotFoundError
from soliplex_workspace.models import FileInfo
from soliplex_workspace.models import WorkspaceInfo


class MockWorkspaceProvider:
    """In-memory workspace provider for unit tests.

    Stores files as ``{room_id: {path: bytes}}``.
    Implements the full ``WorkspaceProvider`` protocol.
    """

    def __init__(self) -> None:
        self._workspaces: dict[str, WorkspaceInfo] = {}
        self._files: dict[str, dict[str, bytes]] = {}
        self._dirs: dict[str, set[str]] = {}

    async def create_workspace(
        self,
        room_id: str,
        name: str,
        quota_bytes: int | None = None,
    ) -> WorkspaceInfo:
        info = WorkspaceInfo(
            room_id=room_id,
            name=name,
            quota_bytes=quota_bytes,
        )
        self._workspaces[room_id] = info
        self._files[room_id] = {}
        self._dirs[room_id] = {"/"}
        return info

    async def delete_workspace(self, room_id: str) -> None:
        self._workspaces.pop(room_id, None)
        self._files.pop(room_id, None)
        self._dirs.pop(room_id, None)

    async def get_workspace(
        self,
        room_id: str,
    ) -> WorkspaceInfo | None:
        return self._workspaces.get(room_id)

    async def list_files(
        self,
        room_id: str,
        path: str = "/",
    ) -> list[FileInfo]:
        self._require_workspace(room_id)
        path = _normalize(path)

        room_dirs = self._dirs.get(room_id, set())
        dir_entries = [
            FileInfo(
                name=posixpath.basename(d),
                path=d,
                is_directory=True,
            )
            for d in sorted(room_dirs)
            if posixpath.dirname(d) == path and d != path
        ]

        room_files = self._files.get(room_id, {})
        file_entries = [
            FileInfo(
                name=posixpath.basename(fpath),
                path=fpath,
                size_bytes=len(content),
            )
            for fpath, content in sorted(room_files.items())
            if posixpath.dirname(fpath) == path
        ]

        return dir_entries + file_entries

    async def upload_file(
        self,
        room_id: str,
        path: str,
        content: bytes,
    ) -> FileInfo:
        self._require_workspace(room_id)
        path = _normalize(path)
        self._files[room_id][path] = content
        return FileInfo(
            name=posixpath.basename(path),
            path=path,
            size_bytes=len(content),
        )

    async def download_file(
        self,
        room_id: str,
        path: str,
    ) -> bytes:
        self._require_workspace(room_id)
        path = _normalize(path)
        room_files = self._files.get(room_id, {})
        if path not in room_files:
            raise WorkspaceFileNotFoundError(room_id, path)
        return room_files[path]

    async def delete_file(
        self,
        room_id: str,
        path: str,
    ) -> None:
        self._require_workspace(room_id)
        path = _normalize(path)
        room_files = self._files.get(room_id, {})
        room_files.pop(path, None)
        room_dirs = self._dirs.get(room_id, set())
        room_dirs.discard(path)

    async def create_folder(
        self,
        room_id: str,
        path: str,
    ) -> FileInfo:
        self._require_workspace(room_id)
        path = _normalize(path)
        self._dirs[room_id].add(path)
        return FileInfo(
            name=posixpath.basename(path),
            path=path,
            is_directory=True,
        )

    async def move(
        self,
        room_id: str,
        src: str,
        dst: str,
    ) -> FileInfo:
        self._require_workspace(room_id)
        src = _normalize(src)
        dst = _normalize(dst)
        room_files = self._files.get(room_id, {})
        if src not in room_files:
            raise WorkspaceFileNotFoundError(room_id, src)
        content = room_files.pop(src)
        room_files[dst] = content
        return FileInfo(
            name=posixpath.basename(dst),
            path=dst,
            size_bytes=len(content),
        )

    async def get_web_ui_url(
        self,
        room_id: str,  # noqa: ARG002
    ) -> str | None:
        return None

    async def get_webdav_url(
        self,
        room_id: str,  # noqa: ARG002
    ) -> str | None:
        return None

    def _require_workspace(self, room_id: str) -> None:
        if room_id not in self._workspaces:
            raise WorkspaceNotFoundError(room_id)


def _normalize(path: str) -> str:
    """Normalize a path to use forward slashes and start with /."""
    path = posixpath.normpath(path)
    if not path.startswith("/"):
        path = "/" + path
    return path
