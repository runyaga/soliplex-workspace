"""Shared utilities for workspace providers."""

from __future__ import annotations

import posixpath

from soliplex_workspace.exceptions import InvalidPathError


def normalize_path(path: str) -> str:
    """Normalize a path to absolute form and reject traversal attempts.

    Raises ``InvalidPathError`` if the path contains ``..`` segments.
    """
    path = path.strip()
    if ".." in path.split("/"):
        raise InvalidPathError(path)
    if not path.startswith("/"):
        path = "/" + path
    return posixpath.normpath(path)
