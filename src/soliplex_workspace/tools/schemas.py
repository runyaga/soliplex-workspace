"""Pydantic response models for LLM workspace tools."""

from pydantic import BaseModel


class FileEntry(BaseModel):
    """Metadata for a single file or directory."""

    name: str
    path: str
    size_bytes: int = 0
    content_type: str = "application/octet-stream"
    is_directory: bool = False
    modified_at: str = ""


class ListResult(BaseModel):
    """Response from workspace_list."""

    path: str
    files: list[FileEntry]
    truncated: bool = False


class ReadResult(BaseModel):
    """Response from workspace_read."""

    path: str
    content: str
    size_bytes: int
    truncated: bool = False


class WriteResult(BaseModel):
    """Response from workspace_write."""

    path: str
    name: str
    size_bytes: int


class SearchResult(BaseModel):
    """Response from workspace_search."""

    pattern: str
    matches: list[FileEntry]
    total: int
    truncated: bool = False


class DeleteResult(BaseModel):
    """Response from workspace_delete."""

    deleted: str
    ok: bool = True


class MoveResult(BaseModel):
    """Response from workspace_move."""

    src: str
    dst: str
    name: str


class CopyResult(BaseModel):
    """Response from workspace_copy."""

    src: str
    dst: str
    name: str
    size_bytes: int
