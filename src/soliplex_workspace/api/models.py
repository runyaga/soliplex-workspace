"""Pydantic request/response models for workspace API."""

from __future__ import annotations

import datetime

from pydantic import BaseModel
from pydantic import Field


class WorkspaceCreateRequest(BaseModel):
    """Request body for creating a workspace."""

    name: str = Field(description="Display name for the workspace")
    quota_bytes: int | None = Field(
        default=None,
        description="Optional quota in bytes",
    )


class WorkspaceInfoResponse(BaseModel):
    """Response body for workspace info."""

    room_id: str
    name: str
    quota_bytes: int | None = None
    used_bytes: int = 0
    web_ui_url: str | None = None
    webdav_url: str | None = None
    created_at: datetime.datetime


class FileInfoResponse(BaseModel):
    """Response body for file/folder info."""

    name: str
    path: str
    size_bytes: int = 0
    content_type: str = "application/octet-stream"
    is_directory: bool = False
    modified_at: datetime.datetime
    etag: str | None = None


class FileListResponse(BaseModel):
    """Response body for listing files."""

    files: list[FileInfoResponse]
    path: str


class MoveRequest(BaseModel):
    """Request body for move/rename."""

    src: str = Field(description="Source path")
    dst: str = Field(description="Destination path")


class FolderCreateRequest(BaseModel):
    """Request body for creating a folder."""

    path: str = Field(description="Folder path to create")
