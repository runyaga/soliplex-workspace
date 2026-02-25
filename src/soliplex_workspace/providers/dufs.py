"""dufs WebDAV workspace provider."""

from __future__ import annotations

import dataclasses
import posixpath
import urllib.parse
from xml.etree import ElementTree

import httpx

from soliplex_workspace.exceptions import DirectoryNotEmptyError
from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import QuotaExceededError
from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.exceptions import WorkspaceNotFoundError
from soliplex_workspace.models import FileInfo
from soliplex_workspace.models import WorkspaceInfo
from soliplex_workspace.utils import normalize_path

_DAV_NS = "DAV:"
_PROPFIND_BODY = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<propfind xmlns="DAV:">'
    "<prop>"
    "<getcontentlength/>"
    "<getcontenttype/>"
    "<getlastmodified/>"
    "<getetag/>"
    "<resourcetype/>"
    "</prop>"
    "</propfind>"
)


def _content_type_for(name: str) -> str:
    """Guess content type from filename extension."""
    ext = posixpath.splitext(name)[1].lower()
    types: dict[str, str] = {
        ".txt": "text/plain",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".json": "application/json",
        ".xml": "application/xml",
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".md": "text/markdown",
        ".csv": "text/csv",
    }
    return types.get(ext, "application/octet-stream")


class DufsWorkspaceProvider:
    """Workspace provider backed by a dufs WebDAV server.

    Each room gets an isolated ``/rooms/{room_id}/`` directory.
    All file operations are performed via WebDAV over HTTP.
    """

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client:
            await self._client.aclose()

    def _room_path(self, room_id: str) -> str:
        """URL path prefix for a room's workspace."""
        return f"/rooms/{room_id}"

    def _url(self, room_id: str, path: str = "/") -> str:
        """Build full URL for a room-scoped path."""
        room_prefix = self._room_path(room_id)
        if path == "/":
            return f"{self._base_url}{room_prefix}/"
        return f"{self._base_url}{room_prefix}{path}"

    async def create_workspace(
        self,
        room_id: str,
        name: str,
        quota_bytes: int | None = None,
    ) -> WorkspaceInfo:
        existing = await self.get_workspace(room_id)
        if existing is not None:
            return existing
        url = self._url(room_id)
        resp = await self._client.request("MKCOL", url)
        if resp.status_code == 405:
            raise WorkspaceAlreadyExistsError(room_id)
        resp.raise_for_status()
        return WorkspaceInfo(
            room_id=room_id,
            name=name,
            quota_bytes=quota_bytes,
            webdav_url=url,
        )

    async def delete_workspace(self, room_id: str) -> None:
        url = self._url(room_id)
        resp = await self._client.request("DELETE", url)
        if resp.status_code == 404:
            return
        resp.raise_for_status()

    async def get_workspace(
        self,
        room_id: str,
    ) -> WorkspaceInfo | None:
        url = self._url(room_id)
        resp = await self._client.request(
            "PROPFIND",
            url,
            headers={"Depth": "0"},
            content=_PROPFIND_BODY,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return WorkspaceInfo(
            room_id=room_id,
            name=room_id,
            webdav_url=url,
        )

    async def get_file_info(
        self,
        room_id: str,
        path: str,
    ) -> FileInfo:
        path = normalize_path(path)
        url = self._url(room_id, path)
        if path != "/" and not url.endswith("/"):
            url_dir = url + "/"
        else:
            url_dir = url
        resp = await self._client.request(
            "PROPFIND",
            url_dir if path == "/" else url,
            headers={"Depth": "0"},
            content=_PROPFIND_BODY,
        )
        if resp.status_code == 404:
            raise WorkspaceFileNotFoundError(room_id, path)
        resp.raise_for_status()
        entries = _parse_propfind(resp.text)
        if not entries:
            raise WorkspaceFileNotFoundError(room_id, path)
        entry = entries[0]
        return FileInfo(
            name=posixpath.basename(path) or "/",
            path=path,
            size_bytes=entry.size,
            content_type=entry.content_type,
            is_directory=entry.is_directory,
            etag=entry.etag,
        )

    async def list_files(
        self,
        room_id: str,
        path: str = "/",
    ) -> list[FileInfo]:
        path = normalize_path(path)
        url = self._url(room_id, path)
        if not url.endswith("/"):
            url += "/"
        resp = await self._client.request(
            "PROPFIND",
            url,
            headers={"Depth": "1"},
            content=_PROPFIND_BODY,
        )
        if resp.status_code == 404:
            raise WorkspaceNotFoundError(room_id)
        resp.raise_for_status()
        entries = _parse_propfind(resp.text)
        room_prefix = self._room_path(room_id)
        result: list[FileInfo] = []
        for entry in entries:
            rel = urllib.parse.urlparse(entry.href).path
            if rel.startswith(room_prefix):
                rel = rel[len(room_prefix) :]
            if not rel or rel == "/":
                rel = "/"
            rel = rel.rstrip("/") or "/"
            entry_path = normalize_path(rel) if rel != "/" else "/"
            if entry_path == path:
                continue
            if posixpath.dirname(entry_path) != path:
                continue
            result.append(
                FileInfo(
                    name=posixpath.basename(entry_path),
                    path=entry_path,
                    size_bytes=entry.size,
                    content_type=entry.content_type,
                    is_directory=entry.is_directory,
                    etag=entry.etag,
                )
            )
        return sorted(result, key=lambda f: (not f.is_directory, f.name))

    async def upload_file(
        self,
        room_id: str,
        path: str,
        content: bytes,
    ) -> FileInfo:
        path = normalize_path(path)
        await self._ensure_workspace(room_id)
        parent = posixpath.dirname(path)
        if parent and parent != "/":
            await self._ensure_parents(room_id, parent)
        url = self._url(room_id, path)
        ct = _content_type_for(posixpath.basename(path))
        resp = await self._client.put(
            url,
            content=content,
            headers={"Content-Type": ct},
        )
        if resp.status_code == 507:
            raise QuotaExceededError(room_id)
        resp.raise_for_status()
        return FileInfo(
            name=posixpath.basename(path),
            path=path,
            size_bytes=len(content),
            content_type=ct,
        )

    async def download_file(
        self,
        room_id: str,
        path: str,
    ) -> bytes:
        path = normalize_path(path)
        url = self._url(room_id, path)
        resp = await self._client.get(url)
        if resp.status_code == 404:
            raise WorkspaceFileNotFoundError(room_id, path)
        resp.raise_for_status()
        return resp.content

    async def delete_file(
        self,
        room_id: str,
        path: str,
    ) -> None:
        path = normalize_path(path)
        url = self._url(room_id, path)
        resp = await self._client.request("DELETE", url)
        if resp.status_code == 404:
            raise WorkspaceFileNotFoundError(room_id, path)
        if resp.status_code == 409:
            raise DirectoryNotEmptyError(room_id, path)
        resp.raise_for_status()

    async def create_folder(
        self,
        room_id: str,
        path: str,
    ) -> FileInfo:
        path = normalize_path(path)
        await self._ensure_workspace(room_id)
        parent = posixpath.dirname(path)
        if parent and parent != "/":
            await self._ensure_parents(room_id, parent)
        url = self._url(room_id, path)
        if not url.endswith("/"):
            url += "/"
        resp = await self._client.request("MKCOL", url)
        resp.raise_for_status()
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
        src = normalize_path(src)
        dst = normalize_path(dst)
        if dst == src or dst.startswith(src + "/"):
            raise InvalidPathError(dst)
        src_url = self._url(room_id, src)
        dst_url = self._url(room_id, dst)
        resp = await self._client.request(
            "MOVE",
            src_url,
            headers={"Destination": dst_url},
        )
        if resp.status_code == 404:
            raise WorkspaceFileNotFoundError(room_id, src)
        resp.raise_for_status()
        return await self.get_file_info(room_id, dst)

    async def list_files_recursive(
        self,
        room_id: str,
        path: str = "/",
        max_depth: int = 10,
        max_results: int = 1000,
    ) -> list[FileInfo]:
        """BFS walk using Depth-1 PROPFIND calls."""
        path = normalize_path(path)
        max_depth = min(max_depth, 20)
        results: list[FileInfo] = []
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(path, 0)]

        while queue and len(results) < max_results:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            try:
                entries = await self.list_files(room_id, current)
            except (WorkspaceNotFoundError, WorkspaceFileNotFoundError):
                continue

            for entry in entries:
                if len(results) >= max_results:
                    break
                results.append(entry)
                if entry.is_directory and depth + 1 < max_depth:
                    queue.append((entry.path, depth + 1))

        return sorted(results, key=lambda f: f.path)

    async def read_text(
        self,
        room_id: str,
        path: str,
        encoding: str = "utf-8",
        max_bytes: int = 100_000,
    ) -> str:
        data = await self.download_file(room_id, path)
        return data[:max_bytes].decode(encoding)

    async def write_text(
        self,
        room_id: str,
        path: str,
        content: str,
        encoding: str = "utf-8",
    ) -> FileInfo:
        return await self.upload_file(room_id, path, content.encode(encoding))

    async def get_web_ui_url(
        self,
        room_id: str,
    ) -> str | None:
        return self._url(room_id)

    async def get_webdav_url(
        self,
        room_id: str,
    ) -> str | None:
        return self._url(room_id)

    async def _ensure_workspace(self, room_id: str) -> None:
        """Ensure the room directory exists on dufs."""
        url = self._url(room_id)
        resp = await self._client.request(
            "PROPFIND",
            url,
            headers={"Depth": "0"},
            content=_PROPFIND_BODY,
        )
        if resp.status_code == 404:
            raise WorkspaceNotFoundError(room_id)

    async def _ensure_parents(
        self,
        room_id: str,
        path: str,
    ) -> None:
        """Create parent directories if they don't exist."""
        parts = path.strip("/").split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}"
            url = self._url(room_id, current)
            if not url.endswith("/"):
                url += "/"
            await self._client.request("MKCOL", url)


@dataclasses.dataclass
class _PropEntry:
    """Parsed entry from a PROPFIND multistatus response."""

    href: str = ""
    size: int = 0
    content_type: str = "application/octet-stream"
    is_directory: bool = False
    etag: str | None = None


def _parse_propfind(xml_text: str) -> list[_PropEntry]:
    """Parse a PROPFIND multistatus XML response."""
    try:
        root = ElementTree.fromstring(xml_text)  # noqa: B314
    except ElementTree.ParseError:
        return []

    entries: list[_PropEntry] = []
    for response in root.findall(f"{{{_DAV_NS}}}response"):
        href_el = response.find(f"{{{_DAV_NS}}}href")
        href = href_el.text if href_el is not None else ""

        entry = _PropEntry(href=href or "")

        propstat = response.find(f"{{{_DAV_NS}}}propstat")
        if propstat is None:
            entries.append(entry)
            continue

        prop = propstat.find(f"{{{_DAV_NS}}}prop")
        if prop is None:
            entries.append(entry)
            continue

        rt = prop.find(f"{{{_DAV_NS}}}resourcetype")
        if rt is not None:
            col = rt.find(f"{{{_DAV_NS}}}collection")
            entry.is_directory = col is not None

        cl = prop.find(f"{{{_DAV_NS}}}getcontentlength")
        if cl is not None and cl.text:
            entry.size = int(cl.text)

        ct = prop.find(f"{{{_DAV_NS}}}getcontenttype")
        if ct is not None and ct.text:
            entry.content_type = ct.text

        etag_el = prop.find(f"{{{_DAV_NS}}}getetag")
        if etag_el is not None and etag_el.text:
            entry.etag = etag_el.text.strip('"')

        entries.append(entry)
    return entries
