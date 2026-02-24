"""Tests for MockWorkspaceProvider."""

import pytest

from soliplex_workspace.exceptions import DirectoryNotEmptyError
from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.exceptions import WorkspaceNotFoundError
from soliplex_workspace.providers.mock import MockWorkspaceProvider


@pytest.fixture
def provider():
    return MockWorkspaceProvider()


class TestCreateWorkspace:
    async def test_create_returns_workspace_info(self, provider):
        info = await provider.create_workspace("room-1", "Test Room")
        assert info.room_id == "room-1"
        assert info.name == "Test Room"

    async def test_create_duplicate_raises(self, provider):
        await provider.create_workspace("room-1", "Test")
        with pytest.raises(WorkspaceAlreadyExistsError):
            await provider.create_workspace("room-1", "Test Again")

    async def test_create_with_quota(self, provider):
        info = await provider.create_workspace(
            "room-1", "Test", quota_bytes=1024
        )
        assert info.quota_bytes == 1024


class TestGetWorkspace:
    async def test_get_existing(self, provider):
        await provider.create_workspace("room-1", "Test")
        info = await provider.get_workspace("room-1")
        assert info is not None
        assert info.room_id == "room-1"

    async def test_get_nonexistent(self, provider):
        result = await provider.get_workspace("nope")
        assert result is None


class TestGetFileInfo:
    async def test_get_file_info(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.upload_file("room-1", "/doc.pdf", b"pdf-bytes")
        info = await provider.get_file_info("room-1", "/doc.pdf")
        assert info.name == "doc.pdf"
        assert info.path == "/doc.pdf"
        assert info.size_bytes == 9

    async def test_get_directory_info(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/notes")
        info = await provider.get_file_info("room-1", "/notes")
        assert info.is_directory is True
        assert info.name == "notes"

    async def test_get_root_info(self, provider):
        await provider.create_workspace("room-1", "Test")
        info = await provider.get_file_info("room-1", "/")
        assert info.is_directory is True
        assert info.name == "/"

    async def test_get_nonexistent(self, provider):
        await provider.create_workspace("room-1", "Test")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.get_file_info("room-1", "/nope.txt")


class TestUploadFile:
    async def test_upload_returns_file_info(self, provider):
        await provider.create_workspace("room-1", "Test")
        info = await provider.upload_file("room-1", "/doc.pdf", b"pdf-content")
        assert info.name == "doc.pdf"
        assert info.path == "/doc.pdf"
        assert info.size_bytes == 11

    async def test_upload_to_nonexistent_workspace(self, provider):
        with pytest.raises(WorkspaceNotFoundError):
            await provider.upload_file("nope", "/doc.pdf", b"content")


class TestListFiles:
    async def test_list_after_upload(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.upload_file("room-1", "/doc.pdf", b"content")
        files = await provider.list_files("room-1")
        assert len(files) == 1
        assert files[0].name == "doc.pdf"

    async def test_list_empty_workspace(self, provider):
        await provider.create_workspace("room-1", "Test")
        files = await provider.list_files("room-1")
        assert files == []

    async def test_list_nonexistent_workspace(self, provider):
        with pytest.raises(WorkspaceNotFoundError):
            await provider.list_files("nope")


class TestDownloadFile:
    async def test_download_existing(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.upload_file("room-1", "/doc.pdf", b"pdf-bytes")
        content = await provider.download_file("room-1", "/doc.pdf")
        assert content == b"pdf-bytes"

    async def test_download_nonexistent(self, provider):
        await provider.create_workspace("room-1", "Test")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.download_file("room-1", "/nope.txt")


class TestDeleteFile:
    async def test_delete_removes_file(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.upload_file("room-1", "/doc.pdf", b"content")
        await provider.delete_file("room-1", "/doc.pdf")
        files = await provider.list_files("room-1")
        assert files == []

    async def test_delete_empty_folder(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/notes")
        await provider.delete_file("room-1", "/notes")
        files = await provider.list_files("room-1")
        assert files == []

    async def test_delete_nonempty_folder_raises(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/notes")
        await provider.upload_file("room-1", "/notes/a.txt", b"hi")
        with pytest.raises(DirectoryNotEmptyError):
            await provider.delete_file("room-1", "/notes")

    async def test_delete_folder_with_subdirs_raises(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/notes")
        await provider.create_folder("room-1", "/notes/sub")
        with pytest.raises(DirectoryNotEmptyError):
            await provider.delete_file("room-1", "/notes")

    async def test_delete_nonexistent_raises(self, provider):
        await provider.create_workspace("room-1", "Test")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.delete_file("room-1", "/nope.txt")


class TestCreateFolder:
    async def test_create_folder_returns_dir_info(self, provider):
        await provider.create_workspace("room-1", "Test")
        info = await provider.create_folder("room-1", "/notes")
        assert info.is_directory is True
        assert info.name == "notes"

    async def test_folder_appears_in_listing(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/notes")
        files = await provider.list_files("room-1")
        assert len(files) == 1
        assert files[0].is_directory is True


class TestMoveFile:
    async def test_move_renames_file(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.upload_file("room-1", "/a.txt", b"hello")
        info = await provider.move("room-1", "/a.txt", "/b.txt")
        assert info.path == "/b.txt"
        assert info.name == "b.txt"

    async def test_move_old_path_gone(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.upload_file("room-1", "/a.txt", b"hello")
        await provider.move("room-1", "/a.txt", "/b.txt")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.download_file("room-1", "/a.txt")

    async def test_move_nonexistent(self, provider):
        await provider.create_workspace("room-1", "Test")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.move("room-1", "/nope.txt", "/b.txt")

    async def test_move_into_self_rejected(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/a")
        with pytest.raises(InvalidPathError):
            await provider.move("room-1", "/a", "/a/b")

    async def test_move_to_same_path_rejected(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.upload_file("room-1", "/a.txt", b"data")
        with pytest.raises(InvalidPathError):
            await provider.move("room-1", "/a.txt", "/a.txt")

    async def test_move_directory(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/old")
        await provider.upload_file("room-1", "/old/a.txt", b"content")
        await provider.create_folder("room-1", "/old/sub")
        info = await provider.move("room-1", "/old", "/new")
        assert info.is_directory is True
        assert info.path == "/new"
        # Children moved too
        content = await provider.download_file("room-1", "/new/a.txt")
        assert content == b"content"
        sub = await provider.get_file_info("room-1", "/new/sub")
        assert sub.is_directory is True

    async def test_move_directory_preserves_sibling_files(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/old")
        await provider.upload_file("room-1", "/old/a.txt", b"child")
        await provider.upload_file("room-1", "/root.txt", b"sibling")
        await provider.move("room-1", "/old", "/new")
        # Sibling file untouched
        content = await provider.download_file("room-1", "/root.txt")
        assert content == b"sibling"

    async def test_move_directory_old_gone(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.create_folder("room-1", "/old")
        await provider.upload_file("room-1", "/old/a.txt", b"data")
        await provider.move("room-1", "/old", "/new")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.get_file_info("room-1", "/old")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.download_file("room-1", "/old/a.txt")


class TestDeleteWorkspace:
    async def test_delete_removes_workspace(self, provider):
        await provider.create_workspace("room-1", "Test")
        await provider.delete_workspace("room-1")
        result = await provider.get_workspace("room-1")
        assert result is None


class TestCrossRoomIsolation:
    async def test_rooms_are_isolated(self, provider):
        await provider.create_workspace("room-1", "Room 1")
        await provider.create_workspace("room-2", "Room 2")
        await provider.upload_file("room-1", "/secret.txt", b"secret")
        files = await provider.list_files("room-2")
        assert files == []


class TestPathNormalization:
    async def test_relative_path_normalized(self, provider):
        await provider.create_workspace("room-1", "Test")
        info = await provider.upload_file("room-1", "doc.pdf", b"content")
        assert info.path == "/doc.pdf"

    async def test_dot_dot_rejected(self, provider):
        await provider.create_workspace("room-1", "Test")
        with pytest.raises(InvalidPathError):
            await provider.upload_file("room-1", "../secret", b"content")

    async def test_nested_traversal_rejected(self, provider):
        await provider.create_workspace("room-1", "Test")
        with pytest.raises(InvalidPathError):
            await provider.download_file("room-1", "/a/../../etc/passwd")

    async def test_dot_segment_allowed(self, provider):
        await provider.create_workspace("room-1", "Test")
        info = await provider.upload_file("room-1", "/a/./b.txt", b"ok")
        assert info.path == "/a/b.txt"


class TestUrlMethods:
    async def test_web_ui_url_returns_none(self, provider):
        await provider.create_workspace("room-1", "Test")
        url = await provider.get_web_ui_url("room-1")
        assert url is None

    async def test_webdav_url_returns_none(self, provider):
        await provider.create_workspace("room-1", "Test")
        url = await provider.get_webdav_url("room-1")
        assert url is None
