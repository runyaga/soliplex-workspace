"""Tests for exception types."""

from soliplex_workspace.exceptions import DirectoryNotEmptyError
from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import QuotaExceededError
from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.exceptions import WorkspaceDisabledError
from soliplex_workspace.exceptions import WorkspaceError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.exceptions import WorkspaceNotFoundError


class TestExceptionHierarchy:
    def test_all_inherit_from_workspace_error(self):
        assert issubclass(WorkspaceDisabledError, WorkspaceError)
        assert issubclass(WorkspaceNotFoundError, WorkspaceError)
        assert issubclass(WorkspaceAlreadyExistsError, WorkspaceError)
        assert issubclass(WorkspaceFileNotFoundError, WorkspaceError)
        assert issubclass(DirectoryNotEmptyError, WorkspaceError)
        assert issubclass(InvalidPathError, WorkspaceError)
        assert issubclass(QuotaExceededError, WorkspaceError)


class TestExceptionMessages:
    def test_workspace_already_exists(self):
        exc = WorkspaceAlreadyExistsError("room-1")
        assert exc.room_id == "room-1"
        assert "room-1" in str(exc)

    def test_directory_not_empty(self):
        exc = DirectoryNotEmptyError("room-1", "/notes")
        assert exc.room_id == "room-1"
        assert exc.path == "/notes"
        assert "/notes" in str(exc)

    def test_invalid_path(self):
        exc = InvalidPathError("../secret")
        assert exc.path == "../secret"
        assert "../secret" in str(exc)

    def test_quota_exceeded(self):
        exc = QuotaExceededError("room-1")
        assert exc.room_id == "room-1"
        assert "room-1" in str(exc)
