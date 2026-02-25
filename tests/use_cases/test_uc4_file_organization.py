"""UC4: File Organization — list(recursive) → mkdir → move → copy."""

from __future__ import annotations

from soliplex_workspace.tools.core import workspace_copy
from soliplex_workspace.tools.core import workspace_list
from soliplex_workspace.tools.core import workspace_mkdir
from soliplex_workspace.tools.core import workspace_move

from .conftest import requires_dufs


@requires_dufs
class TestFileOrganization:
    async def test_organize_flat_files_into_folders(self, workspace):
        p, rid = workspace

        # Upload flat mix of files
        await p.upload_file(rid, "/readme.md", b"# README")
        await p.upload_file(rid, "/notes.md", b"# Notes")
        await p.upload_file(rid, "/logo.png", b"\x89PNG\r\n")
        await p.upload_file(rid, "/main.py", b"print('hello')")

        # Verify flat structure
        flat = await workspace_list(p, rid, recursive=True)
        assert len(flat.files) == 4

        # Create category folders
        await workspace_mkdir(p, rid, "/documents")
        await workspace_mkdir(p, rid, "/images")
        await workspace_mkdir(p, rid, "/code")

        # Copy readme as backup before moving
        await workspace_copy(
            p, rid, "/readme.md", "/documents/readme_backup.md"
        )

        # Move files into folders
        await workspace_move(p, rid, "/readme.md", "/documents/readme.md")
        await workspace_move(p, rid, "/notes.md", "/documents/notes.md")
        await workspace_move(p, rid, "/logo.png", "/images/logo.png")
        await workspace_move(p, rid, "/main.py", "/code/main.py")

        # Verify organized structure
        tree = await workspace_list(p, rid, recursive=True)
        paths = [f.path for f in tree.files]
        assert "/documents/readme.md" in paths
        assert "/documents/readme_backup.md" in paths
        assert "/documents/notes.md" in paths
        assert "/images/logo.png" in paths
        assert "/code/main.py" in paths
        # Originals should be gone from root
        assert "/readme.md" not in paths
        assert "/notes.md" not in paths
        assert "/logo.png" not in paths
        assert "/main.py" not in paths
