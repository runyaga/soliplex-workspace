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
        from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError

        if room_id in self._workspaces:
            raise WorkspaceAlreadyExistsError(room_id)
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

    async def get_file_info(
        self,
        room_id: str,
        path: str,
    ) -> FileInfo:
        self._require_workspace(room_id)
        path = _normalize(path)
        room_files = self._files.get(room_id, {})
        if path in room_files:
            return FileInfo(
                name=posixpath.basename(path),
                path=path,
                size_bytes=len(room_files[path]),
            )
        room_dirs = self._dirs.get(room_id, set())
        if path in room_dirs:
            return FileInfo(
                name=posixpath.basename(path) or "/",
                path=path,
                is_directory=True,
            )
        raise WorkspaceFileNotFoundError(room_id, path)

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
        from soliplex_workspace.exceptions import DirectoryNotEmptyError

        self._require_workspace(room_id)
        path = _normalize(path)
        room_files = self._files.get(room_id, {})
        room_dirs = self._dirs.get(room_id, set())

        if path in room_files:
            room_files.pop(path)
            return

        if path in room_dirs and path != "/":
            # Check for children
            prefix = path + "/"
            has_children = any(
                f.startswith(prefix) for f in room_files
            ) or any(d.startswith(prefix) for d in room_dirs)
            if has_children:
                raise DirectoryNotEmptyError(room_id, path)
            room_dirs.discard(path)
            return

        raise WorkspaceFileNotFoundError(room_id, path)

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
        from soliplex_workspace.exceptions import InvalidPathError

        self._require_workspace(room_id)
        src = _normalize(src)
        dst = _normalize(dst)
        if dst == src or dst.startswith(src + "/"):
            raise InvalidPathError(dst)
        room_files = self._files.get(room_id, {})
        room_dirs = self._dirs.get(room_id, set())

        if src in room_files:
            content = room_files.pop(src)
            room_files[dst] = content
            return FileInfo(
                name=posixpath.basename(dst),
                path=dst,
                size_bytes=len(content),
            )

        if src in room_dirs and src != "/":
            room_dirs.discard(src)
            room_dirs.add(dst)
            # Move all children under src to dst
            src_prefix = src + "/"
            for fpath in list(room_files):
                if fpath.startswith(src_prefix):
                    new_path = dst + fpath[len(src) :]
                    room_files[new_path] = room_files.pop(fpath)
            for dpath in list(room_dirs):
                if dpath.startswith(src_prefix):
                    room_dirs.discard(dpath)
                    room_dirs.add(dst + dpath[len(src) :])
            return FileInfo(
                name=posixpath.basename(dst),
                path=dst,
                is_directory=True,
            )

        raise WorkspaceFileNotFoundError(room_id, src)

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
    """Normalize a path to absolute form and reject traversal attempts.

    Raises ``InvalidPathError`` if the path contains ``..`` segments.
    """
    from soliplex_workspace.exceptions import InvalidPathError

    if ".." in path.split("/"):
        raise InvalidPathError(path)
    if not path.startswith("/"):
        path = "/" + path
    return posixpath.normpath(path)
