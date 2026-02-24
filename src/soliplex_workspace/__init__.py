"""Soliplex Workspace -- persistent file workspaces for rooms."""

from soliplex_workspace.exceptions import WorkspaceDisabledError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.models import FileInfo
from soliplex_workspace.models import WorkspaceInfo
from soliplex_workspace.protocol import WorkspaceProvider

__all__ = [
    "FileInfo",
    "WorkspaceDisabledError",
    "WorkspaceFileNotFoundError",
    "WorkspaceInfo",
    "WorkspaceProvider",
]
