"""Exception-to-HTTPException mapping for workspace API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from soliplex_workspace.exceptions import DirectoryNotEmptyError
from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import QuotaExceededError
from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.exceptions import WorkspaceDisabledError
from soliplex_workspace.exceptions import WorkspaceError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.exceptions import WorkspaceNotFoundError

_STATUS_MAP: dict[type[WorkspaceError], int] = {
    WorkspaceNotFoundError: 404,
    WorkspaceAlreadyExistsError: 409,
    WorkspaceFileNotFoundError: 404,
    DirectoryNotEmptyError: 409,
    InvalidPathError: 400,
    QuotaExceededError: 413,
    WorkspaceDisabledError: 503,
}


async def _workspace_error_handler(
    request: Request,  # noqa: ARG001
    exc: WorkspaceError,
) -> JSONResponse:
    status = _STATUS_MAP.get(type(exc), 500)
    return JSONResponse(
        status_code=status,
        content={"detail": str(exc)},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register workspace exception handlers on the app."""
    app.add_exception_handler(
        WorkspaceError,
        _workspace_error_handler,  # type: ignore[arg-type]
    )
