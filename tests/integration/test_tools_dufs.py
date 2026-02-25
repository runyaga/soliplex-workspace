"""Integration tests for LLM workspace tools against real dufs."""

from __future__ import annotations

import pytest

from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.tools.core import workspace_copy
from soliplex_workspace.tools.core import workspace_find
from soliplex_workspace.tools.core import workspace_list
from soliplex_workspace.tools.core import workspace_read
from soliplex_workspace.tools.core import workspace_write

from .conftest import requires_dufs


@requires_dufs
class TestToolsIntegration:
    async def test_list_recursive_real(self, dufs_workspace):
        p, rid, _ = dufs_workspace
        await p.create_folder(rid, "/a")
        await p.create_folder(rid, "/a/b")
        await p.upload_file(rid, "/a/b/deep.txt", b"deep")
        await p.upload_file(rid, "/top.txt", b"top")
        result = await workspace_list(p, rid, recursive=True)
        paths = [f.path for f in result.files]
        assert "/a" in paths
        assert "/a/b" in paths
        assert "/a/b/deep.txt" in paths
        assert "/top.txt" in paths

    async def test_list_recursive_truncated(self, dufs_workspace):
        p, rid, _ = dufs_workspace
        for i in range(10):
            await p.upload_file(rid, f"/f{i}.txt", b"x")
        result = await workspace_list(p, rid, recursive=True, max_results=3)
        assert len(result.files) <= 3
        assert result.truncated is True

    async def test_read_write_cycle(self, dufs_workspace):
        p, rid, _ = dufs_workspace
        content = "Hello, workspace!\nLine 2."
        await workspace_write(p, rid, "/note.md", content)
        result = await workspace_read(p, rid, "/note.md")
        assert result.content == content
        assert result.truncated is False

    async def test_read_truncated(self, dufs_workspace):
        p, rid, _ = dufs_workspace
        big = "x" * 500
        await workspace_write(p, rid, "/big.txt", big)
        result = await workspace_read(p, rid, "/big.txt", max_bytes=100)
        assert len(result.content) == 100
        assert result.truncated is True

    async def test_write_overwrite_protection(self, dufs_workspace):
        p, rid, _ = dufs_workspace
        await workspace_write(p, rid, "/existing.txt", "first")
        with pytest.raises(WorkspaceAlreadyExistsError):
            await workspace_write(p, rid, "/existing.txt", "second")

    async def test_search_real(self, dufs_workspace):
        p, rid, _ = dufs_workspace
        await p.upload_file(rid, "/report.csv", b"data")
        await p.upload_file(rid, "/notes.md", b"notes")
        await p.upload_file(rid, "/data.csv", b"more")
        result = await workspace_find(p, rid, "*.csv")
        names = [m.name for m in result.matches]
        assert "report.csv" in names
        assert "data.csv" in names
        assert "notes.md" not in names

    async def test_copy_binary(self, dufs_workspace):
        p, rid, _ = dufs_workspace
        binary = bytes(range(256))
        await p.upload_file(rid, "/src.bin", binary)
        result = await workspace_copy(p, rid, "/src.bin", "/dst.bin")
        assert result.size_bytes == 256
        data = await p.download_file(rid, "/dst.bin")
        assert data == binary

    async def test_full_use_case_synthesis(self, dufs_workspace):
        """End-to-end: upload research files, search, read, write."""
        p, rid, _ = dufs_workspace
        await p.create_folder(rid, "/research")
        await p.upload_file(
            rid, "/research/paper1.md", b"# Paper 1\nFindings..."
        )
        await p.upload_file(
            rid, "/research/paper2.md", b"# Paper 2\nResults..."
        )
        await p.upload_file(rid, "/research/data.csv", b"a,b\n1,2")

        search = await workspace_find(p, rid, "*.md", path="/research")
        assert search.total == 2

        contents = []
        for match in search.matches:
            r = await workspace_read(p, rid, match.path)
            contents.append(r.content)

        synthesis = "\n\n".join(contents)
        w = await workspace_write(p, rid, "/research/synthesis.md", synthesis)
        assert w.size_bytes > 0

        verify = await workspace_read(p, rid, "/research/synthesis.md")
        assert "Paper 1" in verify.content
        assert "Paper 2" in verify.content
