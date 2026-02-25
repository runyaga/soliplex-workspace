"""Tests for LLM workspace tools (MockWorkspaceProvider)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from soliplex_workspace.exceptions import InvalidPathError
from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.exceptions import WorkspaceFileNotFoundError
from soliplex_workspace.exceptions import WorkspaceNotFoundError
from soliplex_workspace.providers.mock import MockWorkspaceProvider
from soliplex_workspace.tools.core import workspace_copy
from soliplex_workspace.tools.core import workspace_delete
from soliplex_workspace.tools.core import workspace_find
from soliplex_workspace.tools.core import workspace_info
from soliplex_workspace.tools.core import workspace_list
from soliplex_workspace.tools.core import workspace_mkdir
from soliplex_workspace.tools.core import workspace_move
from soliplex_workspace.tools.core import workspace_read
from soliplex_workspace.tools.core import workspace_write


@pytest.fixture
async def ctx():
    """Provider + room_id with a pre-created workspace."""
    p = MockWorkspaceProvider()
    await p.create_workspace("room-1", "Test Room")
    return p, "room-1"


# ── workspace_list ──────────────────────────────────────────────


class TestWorkspaceList:
    async def test_list_root(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"aaa")
        result = await workspace_list(p, rid)
        assert result.path == "/"
        assert len(result.files) == 1
        assert result.files[0].name == "a.txt"

    async def test_list_subdirectory(self, ctx):
        p, rid = ctx
        await p.create_folder(rid, "/sub")
        await p.upload_file(rid, "/sub/f.txt", b"x")
        result = await workspace_list(p, rid, path="/sub")
        assert result.path == "/sub"
        assert len(result.files) == 1

    async def test_list_recursive(self, ctx):
        p, rid = ctx
        await p.create_folder(rid, "/sub")
        await p.upload_file(rid, "/sub/deep.txt", b"d")
        await p.upload_file(rid, "/top.txt", b"t")
        result = await workspace_list(p, rid, recursive=True)
        paths = [f.path for f in result.files]
        assert "/sub" in paths
        assert "/sub/deep.txt" in paths
        assert "/top.txt" in paths

    async def test_max_depth(self, ctx):
        p, rid = ctx
        await p.create_folder(rid, "/a")
        await p.create_folder(rid, "/a/b")
        await p.upload_file(rid, "/a/b/c.txt", b"c")
        result = await workspace_list(p, rid, recursive=True, max_depth=1)
        paths = [f.path for f in result.files]
        assert "/a" in paths
        assert "/a/b" not in paths

    async def test_max_results_truncated(self, ctx):
        p, rid = ctx
        for i in range(10):
            await p.upload_file(rid, f"/f{i}.txt", b"x")
        result = await workspace_list(p, rid, recursive=True, max_results=3)
        assert len(result.files) <= 3
        assert result.truncated is True

    async def test_empty(self, ctx):
        p, rid = ctx
        result = await workspace_list(p, rid)
        assert result.files == []
        assert result.truncated is False

    async def test_error_propagates(self):
        p = MockWorkspaceProvider()
        with pytest.raises(WorkspaceNotFoundError):
            await workspace_list(p, "no-room")


# ── workspace_read ──────────────────────────────────────────────


class TestWorkspaceRead:
    async def test_read_text_file(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/note.md", b"# Hello")
        result = await workspace_read(p, rid, "/note.md")
        assert result.content == "# Hello"
        assert result.size_bytes == 7
        assert result.truncated is False

    async def test_nonexistent_raises(self, ctx):
        p, rid = ctx
        with pytest.raises(WorkspaceFileNotFoundError):
            await workspace_read(p, rid, "/nope.txt")

    async def test_binary_uses_replacement_chars(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/img.bin", b"\x80\x81\x82")
        result = await workspace_read(p, rid, "/img.bin")
        assert "\ufffd" in result.content

    async def test_max_bytes_truncation(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/big.txt", b"x" * 500)
        result = await workspace_read(p, rid, "/big.txt", max_bytes=100)
        assert len(result.content) == 100
        assert result.truncated is True
        assert result.size_bytes == 500


# ── workspace_write ─────────────────────────────────────────────


class TestWorkspaceWrite:
    async def test_write_new_file(self, ctx):
        p, rid = ctx
        result = await workspace_write(p, rid, "/new.txt", "hello")
        assert result.path == "/new.txt"
        assert result.name == "new.txt"
        assert result.size_bytes == 5

    async def test_overwrite_true(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/exist.txt", b"old")
        result = await workspace_write(
            p, rid, "/exist.txt", "new", overwrite=True
        )
        assert result.size_bytes == 3
        data = await p.download_file(rid, "/exist.txt")
        assert data == b"new"

    async def test_overwrite_false_raises_on_existing(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/exist.txt", b"old")
        with pytest.raises(WorkspaceAlreadyExistsError):
            await workspace_write(p, rid, "/exist.txt", "new")

    async def test_metadata_returned(self, ctx):
        p, rid = ctx
        result = await workspace_write(p, rid, "/meta.txt", "content")
        assert result.name == "meta.txt"
        assert result.size_bytes == 7


# ── workspace_info ──────────────────────────────────────────────


class TestWorkspaceInfo:
    async def test_file_info(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/doc.pdf", b"pdf-data")
        result = await workspace_info(p, rid, "/doc.pdf")
        assert result.name == "doc.pdf"
        assert result.size_bytes == 8
        assert result.is_directory is False

    async def test_directory_info(self, ctx):
        p, rid = ctx
        await p.create_folder(rid, "/notes")
        result = await workspace_info(p, rid, "/notes")
        assert result.is_directory is True
        assert result.name == "notes"

    async def test_nonexistent_raises(self, ctx):
        p, rid = ctx
        with pytest.raises(WorkspaceFileNotFoundError):
            await workspace_info(p, rid, "/nope.txt")


# ── workspace_find ────────────────────────────────────────────


class TestWorkspaceSearch:
    async def test_search_by_extension(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"a")
        await p.upload_file(rid, "/b.md", b"b")
        await p.upload_file(rid, "/c.txt", b"c")
        result = await workspace_find(p, rid, "*.txt")
        assert result.total == 2
        names = [m.name for m in result.matches]
        assert "a.txt" in names
        assert "c.txt" in names

    async def test_search_by_prefix(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/report_jan.csv", b"x")
        await p.upload_file(rid, "/report_feb.csv", b"x")
        await p.upload_file(rid, "/notes.md", b"x")
        result = await workspace_find(p, rid, "report_*")
        assert result.total == 2

    async def test_no_matches(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"a")
        result = await workspace_find(p, rid, "*.py")
        assert result.total == 0
        assert result.matches == []

    async def test_search_subdirectory(self, ctx):
        p, rid = ctx
        await p.create_folder(rid, "/sub")
        await p.upload_file(rid, "/sub/f.py", b"x")
        await p.upload_file(rid, "/top.py", b"x")
        result = await workspace_find(p, rid, "*.py", path="/sub")
        assert result.total == 1
        assert result.matches[0].path == "/sub/f.py"

    async def test_max_results(self, ctx):
        p, rid = ctx
        for i in range(10):
            await p.upload_file(rid, f"/f{i}.txt", b"x")
        result = await workspace_find(p, rid, "*.txt", max_results=3)
        assert len(result.matches) == 3
        assert result.total == 10
        assert result.truncated is True

    async def test_pattern_length_cap(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"x")
        long_pattern = "a" * 300
        result = await workspace_find(p, rid, long_pattern)
        assert len(result.pattern) <= 200

    async def test_case_sensitive(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/README.md", b"x")
        await p.upload_file(rid, "/readme.md", b"x")
        result = await workspace_find(p, rid, "README*")
        assert result.total == 1
        assert result.matches[0].name == "README.md"


# ── workspace_mkdir ─────────────────────────────────────────────


class TestWorkspaceMkdir:
    async def test_create_directory(self, ctx):
        p, rid = ctx
        result = await workspace_mkdir(p, rid, "/notes")
        assert result.is_directory is True
        assert result.name == "notes"

    async def test_nested_directory(self, ctx):
        p, rid = ctx
        await workspace_mkdir(p, rid, "/a")
        result = await workspace_mkdir(p, rid, "/a/b")
        assert result.path == "/a/b"


# ── workspace_move ──────────────────────────────────────────────


class TestWorkspaceMove:
    async def test_move_file(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"data")
        result = await workspace_move(p, rid, "/a.txt", "/b.txt")
        assert result.src == "/a.txt"
        assert result.dst == "/b.txt"
        assert result.name == "b.txt"

    async def test_move_directory(self, ctx):
        p, rid = ctx
        await p.create_folder(rid, "/old")
        await p.upload_file(rid, "/old/f.txt", b"x")
        result = await workspace_move(p, rid, "/old", "/new")
        assert result.dst == "/new"

    async def test_nonexistent_raises(self, ctx):
        p, rid = ctx
        with pytest.raises(WorkspaceFileNotFoundError):
            await workspace_move(p, rid, "/nope", "/dst")

    async def test_traversal_in_dst(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"x")
        with pytest.raises(InvalidPathError):
            await workspace_move(p, rid, "/a.txt", "/../escape")


# ── workspace_delete ────────────────────────────────────────────


class TestWorkspaceDelete:
    async def test_delete_file(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"data")
        result = await workspace_delete(p, rid, "/a.txt")
        assert result.deleted == "/a.txt"
        assert result.ok is True

    async def test_delete_folder(self, ctx):
        p, rid = ctx
        await p.create_folder(rid, "/empty")
        result = await workspace_delete(p, rid, "/empty")
        assert result.ok is True

    async def test_nonexistent_raises(self, ctx):
        p, rid = ctx
        with pytest.raises(WorkspaceFileNotFoundError):
            await workspace_delete(p, rid, "/nope.txt")


# ── workspace_copy ──────────────────────────────────────────────


class TestWorkspaceCopy:
    async def test_copy_text_file(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/src.txt", b"hello")
        result = await workspace_copy(p, rid, "/src.txt", "/dst.txt")
        assert result.src == "/src.txt"
        assert result.dst == "/dst.txt"
        assert result.size_bytes == 5
        data = await p.download_file(rid, "/dst.txt")
        assert data == b"hello"

    async def test_copy_binary_file(self, ctx):
        p, rid = ctx
        binary = bytes(range(256))
        await p.upload_file(rid, "/bin.dat", binary)
        result = await workspace_copy(p, rid, "/bin.dat", "/copy.dat")
        assert result.size_bytes == 256
        data = await p.download_file(rid, "/copy.dat")
        assert data == binary

    async def test_nonexistent_src_raises(self, ctx):
        p, rid = ctx
        with pytest.raises(WorkspaceFileNotFoundError):
            await workspace_copy(p, rid, "/nope.txt", "/dst.txt")


# ── Return type checks ─────────────────────────────────────────


class TestReturnTypes:
    async def test_list_returns_basemodel(self, ctx):
        p, rid = ctx
        result = await workspace_list(p, rid)
        assert isinstance(result, BaseModel)

    async def test_read_returns_basemodel(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/f.txt", b"x")
        result = await workspace_read(p, rid, "/f.txt")
        assert isinstance(result, BaseModel)

    async def test_write_returns_basemodel(self, ctx):
        p, rid = ctx
        result = await workspace_write(p, rid, "/f.txt", "x")
        assert isinstance(result, BaseModel)

    async def test_info_returns_basemodel(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/f.txt", b"x")
        result = await workspace_info(p, rid, "/f.txt")
        assert isinstance(result, BaseModel)

    async def test_search_returns_basemodel(self, ctx):
        p, rid = ctx
        result = await workspace_find(p, rid, "*")
        assert isinstance(result, BaseModel)

    async def test_mkdir_returns_basemodel(self, ctx):
        p, rid = ctx
        result = await workspace_mkdir(p, rid, "/dir")
        assert isinstance(result, BaseModel)

    async def test_move_returns_basemodel(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"x")
        result = await workspace_move(p, rid, "/a.txt", "/b.txt")
        assert isinstance(result, BaseModel)

    async def test_delete_returns_basemodel(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"x")
        result = await workspace_delete(p, rid, "/a.txt")
        assert isinstance(result, BaseModel)

    async def test_copy_returns_basemodel(self, ctx):
        p, rid = ctx
        await p.upload_file(rid, "/a.txt", b"x")
        result = await workspace_copy(p, rid, "/a.txt", "/b.txt")
        assert isinstance(result, BaseModel)


# ── Safety tests ────────────────────────────────────────────────


class TestSafety:
    async def test_path_traversal_list(self, ctx):
        p, rid = ctx
        with pytest.raises(InvalidPathError):
            await workspace_list(p, rid, path="/../etc")

    async def test_path_traversal_read(self, ctx):
        p, rid = ctx
        with pytest.raises(InvalidPathError):
            await workspace_read(p, rid, "/../etc/passwd")

    async def test_path_traversal_write(self, ctx):
        p, rid = ctx
        with pytest.raises(InvalidPathError):
            await workspace_write(p, rid, "/../etc/evil", "bad")

    async def test_path_traversal_info(self, ctx):
        p, rid = ctx
        with pytest.raises(InvalidPathError):
            await workspace_info(p, rid, "/../etc/passwd")

    async def test_path_traversal_search(self, ctx):
        p, rid = ctx
        with pytest.raises(InvalidPathError):
            await workspace_find(p, rid, "*", path="/../etc")

    async def test_path_traversal_mkdir(self, ctx):
        p, rid = ctx
        with pytest.raises(InvalidPathError):
            await workspace_mkdir(p, rid, "/../evil")

    async def test_path_traversal_delete(self, ctx):
        p, rid = ctx
        with pytest.raises(InvalidPathError):
            await workspace_delete(p, rid, "/../etc/passwd")

    async def test_path_traversal_copy(self, ctx):
        p, rid = ctx
        with pytest.raises(InvalidPathError):
            await workspace_copy(p, rid, "/../a", "/b")

    async def test_max_depth_clamped_to_20(self, ctx):
        p, rid = ctx
        result = await workspace_list(p, rid, recursive=True, max_depth=999)
        assert isinstance(result.files, list)
