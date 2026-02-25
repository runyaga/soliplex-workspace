"""UC5: Code Documentation — search → read → mkdir → write."""

from __future__ import annotations

from soliplex_workspace.tools.core import workspace_mkdir
from soliplex_workspace.tools.core import workspace_read
from soliplex_workspace.tools.core import workspace_search
from soliplex_workspace.tools.core import workspace_write

from .conftest import requires_dufs


@requires_dufs
class TestCodeDocumentation:
    async def test_generate_api_docs(self, workspace):
        p, rid = workspace

        # Upload Python source files
        await p.create_folder(rid, "/src")
        await p.upload_file(
            rid,
            "/src/main.py",
            b'def hello():\n    """Say hello."""\n    return "hi"\n',
        )
        await p.upload_file(
            rid,
            "/src/utils.py",
            b'def add(a, b):\n    """Add two numbers."""\n    return a + b\n',
        )

        # Search for Python files
        search = await workspace_search(p, rid, "*.py")
        assert search.total == 2

        # Read each file
        docs_parts = []
        for match in sorted(search.matches, key=lambda m: m.path):
            r = await workspace_read(p, rid, match.path)
            docs_parts.append(
                f"## {match.name}\n\n```python\n{r.content}```\n"
            )

        # Write docs
        await workspace_mkdir(p, rid, "/docs")
        doc_content = "# API Reference\n\n" + "\n".join(docs_parts)
        w = await workspace_write(p, rid, "/docs/api.md", doc_content)
        assert w.size_bytes > 0

        # Verify
        verify = await workspace_read(p, rid, "/docs/api.md")
        assert "hello" in verify.content
        assert "add" in verify.content
