"""Data models for workspace operations."""

from __future__ import annotations

import dataclasses
import datetime


@dataclasses.dataclass(frozen=True)
class WorkspaceInfo:
    """Metadata about a room's workspace."""

    room_id: str
    name: str
    quota_bytes: int | None = None
    used_bytes: int = 0
    web_ui_url: str | None = None
    webdav_url: str | None = None
    created_at: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )


@dataclasses.dataclass(frozen=True)
class FileInfo:
    """Metadata about a file or folder in a workspace."""

    name: str
    path: str
    size_bytes: int = 0
    content_type: str = "application/octet-stream"
    is_directory: bool = False
    modified_at: datetime.datetime = dataclasses.field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
    )
    etag: str | None = None
