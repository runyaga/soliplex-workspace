"""LLM workspace tool functions.

Each tool is a plain async function taking ``(provider, room_id, ...)``.
Return types are Pydantic ``BaseModel`` subclasses so LLM frameworks can
introspect schemas.  Errors raise exceptions — ``WorkspaceError``
subclasses bubble up to the framework for retry formatting.
"""

from __future__ import annotations

import fnmatch
import logging
from typing import TYPE_CHECKING

from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.tools.schemas import CopyResult
from soliplex_workspace.tools.schemas import DeleteResult
from soliplex_workspace.tools.schemas import FileEntry
from soliplex_workspace.tools.schemas import ListResult
from soliplex_workspace.tools.schemas import MoveResult
from soliplex_workspace.tools.schemas import ReadResult
from soliplex_workspace.tools.schemas import SearchResult
from soliplex_workspace.tools.schemas import WriteResult
from soliplex_workspace.utils import normalize_path

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from soliplex_workspace.protocol import WorkspaceProvider

_MAX_DEPTH_CEILING = 20
_MAX_PATTERN_LEN = 200


def _file_entry_from_info(info: object) -> FileEntry:
    """Convert a FileInfo dataclass to a FileEntry Pydantic model."""
    return FileEntry(
        name=getattr(info, "name", ""),
        path=getattr(info, "path", ""),
        size_bytes=getattr(info, "size_bytes", 0),
        content_type=getattr(info, "content_type", "application/octet-stream"),
        is_directory=getattr(info, "is_directory", False),
        modified_at=str(getattr(info, "modified_at", "")),
    )


async def workspace_list(
    provider: WorkspaceProvider,
    room_id: str,
    path: str = "/",
    recursive: bool = False,
    max_depth: int = 10,
    max_results: int = 500,
) -> ListResult:
    """List files and folders at the given path.

    Args:
        path: Directory to list (default "/").
        recursive: If True, list all descendants, not just immediate children.
        max_depth: Maximum recursion depth (only used when recursive=True).
        max_results: Cap on number of entries returned.

    Returns a list of file/folder entries with metadata.
    """
    path = normalize_path(path)
    max_depth = min(max_depth, _MAX_DEPTH_CEILING)
    logger.debug(
        "workspace_list room=%s path=%s recursive=%s", room_id, path, recursive
    )

    if recursive:
        entries = await provider.list_files_recursive(
            room_id, path, max_depth=max_depth, max_results=max_results
        )
    else:
        entries = await provider.list_files(room_id, path)

    truncated = len(entries) >= max_results
    files = [_file_entry_from_info(e) for e in entries[:max_results]]
    logger.debug(
        "workspace_list room=%s result: %d files, truncated=%s",
        room_id,
        len(files),
        truncated,
    )
    return ListResult(path=path, files=files, truncated=truncated)


async def workspace_read(
    provider: WorkspaceProvider,
    room_id: str,
    path: str,
    max_bytes: int = 100_000,
) -> ReadResult:
    """Read the text content of a single file.

    Args:
        path: Absolute path to the file (e.g. "/notes/readme.md").
        max_bytes: Truncate after this many bytes (~25k tokens at default).

    Works with code, markdown, CSV, JSON. Raises an error on binary files.
    """
    path = normalize_path(path)
    logger.debug("workspace_read room=%s path=%s", room_id, path)
    raw = await provider.download_file(room_id, path)
    truncated = len(raw) > max_bytes
    text = raw[:max_bytes].decode("utf-8", errors="replace")
    logger.debug(
        "workspace_read room=%s path=%s size=%d truncated=%s",
        room_id,
        path,
        len(raw),
        truncated,
    )
    return ReadResult(
        path=path,
        content=text,
        size_bytes=len(raw),
        truncated=truncated,
    )


async def workspace_write(
    provider: WorkspaceProvider,
    room_id: str,
    path: str,
    content: str,
    overwrite: bool = False,
) -> WriteResult:
    """Create or overwrite a text file.

    Args:
        path: Absolute path for the file (e.g. "/docs/plan.md").
        content: The text content to write.
        overwrite: Must be True to replace an existing file.

    Parent directories are created automatically.
    """
    path = normalize_path(path)
    logger.debug(
        "workspace_write room=%s path=%s overwrite=%s len=%d",
        room_id,
        path,
        overwrite,
        len(content),
    )
    if not overwrite:
        try:
            await provider.get_file_info(room_id, path)
        except WorkspaceFileNotFoundError:
            pass
        else:
            raise WorkspaceAlreadyExistsError(room_id)
    info = await provider.write_text(room_id, path, content)
    logger.debug(
        "workspace_write room=%s path=%s done size=%d",
        room_id,
        path,
        info.size_bytes,
    )
    return WriteResult(
        path=info.path,
        name=info.name,
        size_bytes=info.size_bytes,
    )


async def workspace_info(
    provider: WorkspaceProvider,
    room_id: str,
    path: str,
) -> FileEntry:
    """Get metadata (size, type, modified date) for a single file or folder."""
    path = normalize_path(path)
    logger.debug("workspace_info room=%s path=%s", room_id, path)
    info = await provider.get_file_info(room_id, path)
    return _file_entry_from_info(info)


async def workspace_find(
    provider: WorkspaceProvider,
    room_id: str,
    pattern: str,
    path: str = "/",
    max_results: int = 200,
) -> SearchResult:
    """Find files recursively by glob pattern (like the ``find`` command).

    Matches against filenames only, not file contents. Always searches
    all sub-folders starting from ``path``. This tool does not accept
    a ``recursive`` parameter — it is always recursive.

    Glob examples:
    - ``*.md``  — all markdown files
    - ``report_*`` — files starting with "report_"
    - ``*.py`` — all Python files

    Args:
        pattern: Glob pattern to match against filenames.
        path: Starting directory (default "/").
        max_results: Cap on number of matches returned.

    To list a single directory without recursion, use workspace_list.
    To read file contents, use workspace_read.
    """
    path = normalize_path(path)
    pattern = pattern[:_MAX_PATTERN_LEN]
    logger.debug(
        "workspace_find room=%s pattern=%s path=%s", room_id, pattern, path
    )
    all_files = await provider.list_files_recursive(
        room_id, path, max_depth=20, max_results=10_000
    )
    matches = [
        _file_entry_from_info(f)
        for f in all_files
        if fnmatch.fnmatchcase(f.name, pattern)
    ]
    total = len(matches)
    truncated = total > max_results
    logger.debug(
        "workspace_find room=%s pattern=%s matches=%d",
        room_id,
        pattern,
        total,
    )
    return SearchResult(
        pattern=pattern,
        matches=matches[:max_results],
        total=total,
        truncated=truncated,
    )


async def workspace_mkdir(
    provider: WorkspaceProvider,
    room_id: str,
    path: str,
) -> FileEntry:
    """Create a directory. Safe to call if the directory already exists."""
    path = normalize_path(path)
    logger.debug("workspace_mkdir room=%s path=%s", room_id, path)
    info = await provider.create_folder(room_id, path)
    return _file_entry_from_info(info)


async def workspace_move(
    provider: WorkspaceProvider,
    room_id: str,
    src: str,
    dst: str,
) -> MoveResult:
    """Move or rename a file or folder.

    Args:
        src: Current path of the file/folder.
        dst: New path (can rename and/or relocate).
    """
    src = normalize_path(src)
    dst = normalize_path(dst)
    logger.debug("workspace_move room=%s src=%s dst=%s", room_id, src, dst)
    info = await provider.move(room_id, src, dst)
    return MoveResult(src=src, dst=info.path, name=info.name)


async def workspace_delete(
    provider: WorkspaceProvider,
    room_id: str,
    path: str,
) -> DeleteResult:
    """Permanently delete a file or folder. Cannot be undone."""
    path = normalize_path(path)
    logger.debug("workspace_delete room=%s path=%s", room_id, path)
    await provider.delete_file(room_id, path)
    logger.debug("workspace_delete room=%s path=%s done", room_id, path)
    return DeleteResult(deleted=path)


async def workspace_copy(
    provider: WorkspaceProvider,
    room_id: str,
    src: str,
    dst: str,
) -> CopyResult:
    """Copy a file to a new location (binary-safe).

    Args:
        src: Path of the file to copy.
        dst: Destination path for the copy.
    """
    src = normalize_path(src)
    dst = normalize_path(dst)
    logger.debug("workspace_copy room=%s src=%s dst=%s", room_id, src, dst)
    data = await provider.download_file(room_id, src)
    info = await provider.upload_file(room_id, dst, data)
    logger.debug(
        "workspace_copy room=%s src=%s dst=%s size=%d",
        room_id,
        src,
        dst,
        info.size_bytes,
    )
    return CopyResult(
        src=src,
        dst=info.path,
        name=info.name,
        size_bytes=info.size_bytes,
    )
