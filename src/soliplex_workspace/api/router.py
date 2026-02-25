"""FastAPI router for workspace file operations."""

from __future__ import annotations

import posixpath
import re
from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Response
from fastapi import UploadFile

from soliplex_workspace.api.dependencies import depend_the_workspace_provider
from soliplex_workspace.api.models import FileInfoResponse
from soliplex_workspace.api.models import FileListResponse
from soliplex_workspace.api.models import FolderCreateRequest
from soliplex_workspace.api.models import MoveRequest
from soliplex_workspace.api.models import WorkspaceCreateRequest
from soliplex_workspace.api.models import WorkspaceInfoResponse
from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import WorkspaceNotFoundError
from soliplex_workspace.models import FileInfo
from soliplex_workspace.models import WorkspaceInfo
from soliplex_workspace.protocol import WorkspaceProvider

router = APIRouter(
    prefix="/v1/rooms/{room_id}/workspace",
    tags=["workspace"],
)

Provider = Annotated[
    WorkspaceProvider,
    Depends(depend_the_workspace_provider),
]

_ROOM_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _validate_room_id(room_id: str) -> str:
    """Reject room IDs with traversal or illegal characters."""
    if not _ROOM_ID_RE.match(room_id):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid room_id: {room_id}",
        )
    return room_id


def _validate_path(path: str) -> str:
    """Reject paths with traversal attempts or unsafe characters."""
    if "\\" in path or ".." in path.split("/"):
        raise InvalidPathError(path)
    return path


def _ws_response(ws: WorkspaceInfo) -> WorkspaceInfoResponse:
    return WorkspaceInfoResponse(
        room_id=ws.room_id,
        name=ws.name,
        quota_bytes=ws.quota_bytes,
        used_bytes=ws.used_bytes,
        web_ui_url=ws.web_ui_url,
        webdav_url=ws.webdav_url,
        created_at=ws.created_at,
    )


def _file_response(fi: FileInfo) -> FileInfoResponse:
    return FileInfoResponse(
        name=fi.name,
        path=fi.path,
        size_bytes=fi.size_bytes,
        content_type=fi.content_type,
        is_directory=fi.is_directory,
        modified_at=fi.modified_at,
        etag=fi.etag,
    )


@router.post("", status_code=201)
async def create_workspace(
    room_id: str,
    body: WorkspaceCreateRequest,
    provider: Provider,
) -> WorkspaceInfoResponse:
    _validate_room_id(room_id)
    ws = await provider.create_workspace(room_id, body.name, body.quota_bytes)
    return _ws_response(ws)


@router.get("")
async def get_workspace(
    room_id: str,
    provider: Provider,
) -> WorkspaceInfoResponse:
    _validate_room_id(room_id)
    ws = await provider.get_workspace(room_id)
    if ws is None:
        raise WorkspaceNotFoundError(room_id)
    return _ws_response(ws)


@router.delete("", status_code=204)
async def delete_workspace(
    room_id: str,
    provider: Provider,
) -> Response:
    _validate_room_id(room_id)
    await provider.delete_workspace(room_id)
    return Response(status_code=204)


@router.get("/files")
async def list_files(
    room_id: str,
    provider: Provider,
    path: str = "/",
) -> FileListResponse:
    _validate_room_id(room_id)
    _validate_path(path)
    files = await provider.list_files(room_id, path)
    return FileListResponse(
        files=[_file_response(f) for f in files],
        path=path,
    )


@router.get("/files/info")
async def get_file_info(
    room_id: str,
    provider: Provider,
    path: str = "/",
) -> FileInfoResponse:
    _validate_room_id(room_id)
    _validate_path(path)
    info = await provider.get_file_info(room_id, path)
    return _file_response(info)


@router.post("/files/upload", status_code=201)
async def upload_file(
    room_id: str,
    provider: Provider,
    file: UploadFile,
    path: str = "/",
) -> FileInfoResponse:
    _validate_room_id(room_id)
    _validate_path(path)
    safe_name = posixpath.basename(file.filename or "upload")
    if path == "/":
        dest = f"/{safe_name}"
    else:
        dest = path
    _validate_path(dest)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_UPLOAD_BYTES} bytes)",
        )
    info = await provider.upload_file(room_id, dest, content)
    return _file_response(info)


@router.get("/files/download")
async def download_file(
    room_id: str,
    provider: Provider,
    path: str,
) -> Response:
    _validate_room_id(room_id)
    _validate_path(path)
    content = await provider.download_file(room_id, path)
    info = await provider.get_file_info(room_id, path)
    safe_filename = (
        info.name.replace('"', "'").replace("\r", "").replace("\n", "")
    )
    return Response(
        content=content,
        media_type=info.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
        },
    )


@router.delete("/files", status_code=204)
async def delete_file(
    room_id: str,
    provider: Provider,
    path: str,
) -> Response:
    _validate_room_id(room_id)
    _validate_path(path)
    await provider.delete_file(room_id, path)
    return Response(status_code=204)


@router.post("/folders", status_code=201)
async def create_folder(
    room_id: str,
    body: FolderCreateRequest,
    provider: Provider,
) -> FileInfoResponse:
    _validate_room_id(room_id)
    _validate_path(body.path)
    info = await provider.create_folder(room_id, body.path)
    return _file_response(info)


@router.post("/files/move")
async def move_file(
    room_id: str,
    body: MoveRequest,
    provider: Provider,
) -> FileInfoResponse:
    _validate_room_id(room_id)
    _validate_path(body.src)
    _validate_path(body.dst)
    info = await provider.move(room_id, body.src, body.dst)
    return _file_response(info)
