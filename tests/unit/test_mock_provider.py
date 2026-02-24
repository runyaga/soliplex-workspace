"""Tests for MockWorkspaceProvider."""

import pytest

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


class TestUrlMethods:
    async def test_web_ui_url_returns_none(self, provider):
        await provider.create_workspace("room-1", "Test")
        url = await provider.get_web_ui_url("room-1")
        assert url is None

    async def test_webdav_url_returns_none(self, provider):
        await provider.create_workspace("room-1", "Test")
        url = await provider.get_webdav_url("room-1")
        assert url is None
