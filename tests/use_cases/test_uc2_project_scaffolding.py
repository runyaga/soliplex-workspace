"""UC2: Project Scaffolding — mkdir → write → list(recursive) → read."""

from __future__ import annotations

from soliplex_workspace.tools.core import workspace_list
from soliplex_workspace.tools.core import workspace_mkdir
from soliplex_workspace.tools.core import workspace_read
from soliplex_workspace.tools.core import workspace_write

from .conftest import requires_dufs


@requires_dufs
class TestProjectScaffolding:
    async def test_scaffold_python_project(self, workspace):
        p, rid = workspace

        # Create directory structure
        await workspace_mkdir(p, rid, "/myproject")
        await workspace_mkdir(p, rid, "/myproject/src")
        await workspace_mkdir(p, rid, "/myproject/src/pkg")
        await workspace_mkdir(p, rid, "/myproject/tests")

        # Write project files
        await workspace_write(
            p,
            rid,
            "/myproject/src/pkg/__init__.py",
            '"""My package."""\n',
        )
        await workspace_write(
            p,
            rid,
            "/myproject/README.md",
            "# My Project\n\nA sample project.\n",
        )
        await workspace_write(
            p,
            rid,
            "/myproject/pyproject.toml",
            '[project]\nname = "myproject"\nversion = "0.1.0"\n',
        )

        # Verify full tree
        tree = await workspace_list(p, rid, path="/myproject", recursive=True)
        paths = [f.path for f in tree.files]
        assert "/myproject/src" in paths
        assert "/myproject/src/pkg" in paths
        assert "/myproject/src/pkg/__init__.py" in paths
        assert "/myproject/tests" in paths
        assert "/myproject/README.md" in paths
        assert "/myproject/pyproject.toml" in paths

        # Verify files are readable
        init = await workspace_read(p, rid, "/myproject/src/pkg/__init__.py")
        assert "My package" in init.content

        readme = await workspace_read(p, rid, "/myproject/README.md")
        assert "My Project" in readme.content
