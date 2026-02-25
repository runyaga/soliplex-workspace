"""UC1: Research Synthesis — search → read → write."""

from __future__ import annotations

from soliplex_workspace.tools.core import workspace_read
from soliplex_workspace.tools.core import workspace_search
from soliplex_workspace.tools.core import workspace_write

from .conftest import requires_dufs


@requires_dufs
class TestResearchSynthesis:
    async def test_search_read_synthesize_write(self, workspace):
        p, rid = workspace

        # Upload 3 research files
        await p.create_folder(rid, "/research")
        await p.upload_file(
            rid,
            "/research/paper1.md",
            b"# Paper 1\nKey finding: X works.",
        )
        await p.upload_file(
            rid,
            "/research/paper2.md",
            b"# Paper 2\nConclusion: Y improves Z.",
        )
        await p.upload_file(
            rid,
            "/research/paper3.md",
            b"# Paper 3\nResult: A correlates with B.",
        )

        # Search for markdown files
        search = await workspace_search(p, rid, "*.md", path="/research")
        assert search.total == 3

        # Read each match
        contents = []
        for match in sorted(search.matches, key=lambda m: m.path):
            r = await workspace_read(p, rid, match.path)
            assert len(r.content) > 0
            contents.append(r.content)

        # Synthesize and write
        synthesis = "# Synthesis\n\n" + "\n\n---\n\n".join(contents)
        w = await workspace_write(p, rid, "/research/synthesis.md", synthesis)
        assert w.size_bytes > 0

        # Verify written content
        verify = await workspace_read(p, rid, "/research/synthesis.md")
        assert "Paper 1" in verify.content
        assert "Paper 2" in verify.content
        assert "Paper 3" in verify.content
