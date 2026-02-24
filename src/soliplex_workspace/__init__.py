"""Soliplex Workspace -- persistent file workspaces for rooms."""

from soliplex_workspace.exceptions import DirectoryNotEmptyError
from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import QuotaExceededError
from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.exceptions import WorkspaceDisabledError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.models import FileInfo
from soliplex_workspace.models import WorkspaceInfo
from soliplex_workspace.protocol import WorkspaceProvider

__all__ = [
    "DirectoryNotEmptyError",
    "FileInfo",
    "InvalidPathError",
    "QuotaExceededError",
    "WorkspaceAlreadyExistsError",
    "WorkspaceDisabledError",
    "WorkspaceFileNotFoundError",
    "WorkspaceInfo",
    "WorkspaceProvider",
]
