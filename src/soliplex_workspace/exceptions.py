"""Workspace provider exceptions."""


class WorkspaceError(Exception):
    """Base exception for workspace operations."""


class WorkspaceDisabledError(WorkspaceError):
    """Raised when workspace feature is disabled."""

    def __init__(self) -> None:
        super().__init__("Workspace feature is disabled in this installation")


class WorkspaceNotFoundError(WorkspaceError):
    """Raised when a workspace does not exist."""

    def __init__(self, room_id: str) -> None:
        self.room_id = room_id
        super().__init__(f"No workspace for room: {room_id}")


class WorkspaceFileNotFoundError(WorkspaceError):
    """Raised when a file does not exist in the workspace."""

    def __init__(self, room_id: str, path: str) -> None:
        self.room_id = room_id
        self.path = path
        super().__init__(f"File not found: {path} in room {room_id}")
