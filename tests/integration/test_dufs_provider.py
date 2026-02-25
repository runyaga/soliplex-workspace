"""Integration tests for DufsWorkspaceProvider against real dufs."""

from __future__ import annotations

import asyncio
import uuid

import pytest

from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError

from .conftest import requires_dufs

pytestmark = [requires_dufs, pytest.mark.dufs]


class TestCreateWorkspace:
    async def test_create_workspace_creates_directory(self, dufs_workspace):
        provider, room_id, info = dufs_workspace
        assert info.room_id == room_id
        ws = await provider.get_workspace(room_id)
        assert ws is not None


class TestUploadDownload:
    async def test_upload_and_download_roundtrip(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        content = b"hello world"
        await provider.upload_file(room_id, "/test.txt", content)
        result = await provider.download_file(room_id, "/test.txt")
        assert result == content

    async def test_upload_large_file(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        content = b"x" * (10 * 1024 * 1024)  # 10MB
        await provider.upload_file(room_id, "/large.bin", content)
        result = await provider.download_file(room_id, "/large.bin")
        assert len(result) == len(content)
        assert result == content


class TestListFiles:
    async def test_list_files_after_upload(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.upload_file(room_id, "/a.txt", b"aaa")
        await provider.upload_file(room_id, "/b.txt", b"bbb")
        files = await provider.list_files(room_id)
        names = [f.name for f in files]
        assert "a.txt" in names
        assert "b.txt" in names

    async def test_list_files_in_subfolder(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.create_folder(room_id, "/sub")
        await provider.upload_file(room_id, "/sub/file.txt", b"data")
        files = await provider.list_files(room_id, "/sub")
        assert len(files) == 1
        assert files[0].name == "file.txt"


class TestDeleteFile:
    async def test_delete_file_removes_from_dufs(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.upload_file(room_id, "/del.txt", b"gone")
        await provider.delete_file(room_id, "/del.txt")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.download_file(room_id, "/del.txt")


class TestCreateFolder:
    async def test_create_folder_via_mkcol(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        info = await provider.create_folder(room_id, "/docs")
        assert info.is_directory is True
        assert info.name == "docs"


class TestMoveFile:
    async def test_move_file_via_move(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.upload_file(room_id, "/old.txt", b"data")
        info = await provider.move(room_id, "/old.txt", "/new.txt")
        assert info.path == "/new.txt"
        content = await provider.download_file(room_id, "/new.txt")
        assert content == b"data"

    async def test_move_directory_with_children(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.create_folder(room_id, "/src")
        await provider.upload_file(room_id, "/src/main.py", b"code")
        await provider.move(room_id, "/src", "/dst")
        content = await provider.download_file(room_id, "/dst/main.py")
        assert content == b"code"


class TestGetFileInfo:
    async def test_get_file_info_returns_metadata(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.upload_file(room_id, "/info.txt", b"12345")
        info = await provider.get_file_info(room_id, "/info.txt")
        assert info.name == "info.txt"
        assert info.size_bytes == 5


class TestCrossRoomIsolation:
    async def test_rooms_are_isolated(self, dufs_provider):
        room_a = f"test-a-{uuid.uuid4().hex[:8]}"
        room_b = f"test-b-{uuid.uuid4().hex[:8]}"
        try:
            await dufs_provider.create_workspace(room_a, "Room A")
            await dufs_provider.create_workspace(room_b, "Room B")
            await dufs_provider.upload_file(room_a, "/secret.txt", b"secret")
            files = await dufs_provider.list_files(room_b)
            names = [f.name for f in files]
            assert "secret.txt" not in names
        finally:
            await dufs_provider.delete_workspace(room_a)
            await dufs_provider.delete_workspace(room_b)


class TestDeleteWorkspace:
    async def test_delete_workspace_removes_all(self, dufs_provider):
        room_id = f"test-{uuid.uuid4().hex[:8]}"
        await dufs_provider.create_workspace(room_id, "Temp")
        await dufs_provider.upload_file(room_id, "/file.txt", b"content")
        await dufs_provider.delete_workspace(room_id)
        ws = await dufs_provider.get_workspace(room_id)
        assert ws is None


class TestDeleteNonEmptyDir:
    async def test_delete_nonempty_dir_succeeds(self, dufs_workspace):
        """dufs with -A flag recursively deletes non-empty directories."""
        provider, room_id, _ = dufs_workspace
        await provider.create_folder(room_id, "/full")
        await provider.upload_file(room_id, "/full/child.txt", b"data")
        await provider.delete_file(room_id, "/full")
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.download_file(room_id, "/full/child.txt")


class TestPathTraversal:
    async def test_path_traversal_rejected(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        with pytest.raises(InvalidPathError):
            await provider.upload_file(
                room_id, "/../../../etc/passwd", b"hack"
            )


class TestDownloadNonexistent:
    async def test_download_nonexistent_raises(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        with pytest.raises(WorkspaceFileNotFoundError):
            await provider.download_file(room_id, "/ghost.txt")


class TestContentType:
    async def test_content_type_detection(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.upload_file(room_id, "/doc.pdf", b"pdf")
        info = await provider.get_file_info(room_id, "/doc.pdf")
        assert info.content_type in (
            "application/pdf",
            "application/octet-stream",
        )


class TestSpecialCharacters:
    async def test_special_characters_in_filename(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.upload_file(room_id, "/my file (1).txt", b"data")
        content = await provider.download_file(room_id, "/my file (1).txt")
        assert content == b"data"


class TestOverwriteFile:
    async def test_overwrite_existing_file(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        await provider.upload_file(room_id, "/f.txt", b"v1")
        await provider.upload_file(room_id, "/f.txt", b"v2")
        content = await provider.download_file(room_id, "/f.txt")
        assert content == b"v2"


class TestWebdavUrl:
    async def test_get_webdav_url(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace
        url = await provider.get_webdav_url(room_id)
        assert url is not None
        assert room_id in url


class TestIdempotentCreate:
    async def test_create_workspace_twice_returns_same(self, dufs_provider):
        """Calling create_workspace twice returns existing workspace."""
        room_id = f"test-idem-{uuid.uuid4().hex[:8]}"
        try:
            first = await dufs_provider.create_workspace(room_id, "First")
            assert first.room_id == room_id

            second = await dufs_provider.create_workspace(room_id, "Second")
            assert second.room_id == room_id

            files = await dufs_provider.list_files(room_id)
            assert isinstance(files, list)
        finally:
            await dufs_provider.delete_workspace(room_id)


class TestConcurrentUploads:
    async def test_concurrent_uploads(self, dufs_workspace):
        provider, room_id, _ = dufs_workspace

        async def upload(i: int) -> None:
            await provider.upload_file(
                room_id, f"/file-{i}.txt", f"content-{i}".encode()
            )

        await asyncio.gather(*(upload(i) for i in range(10)))
        files = await provider.list_files(room_id)
        assert len(files) == 10
