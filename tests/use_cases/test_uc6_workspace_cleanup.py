"""UC6: Workspace Cleanup / Audit — list(recursive) → info → delete."""

from __future__ import annotations

from soliplex_workspace.tools.core import workspace_delete
from soliplex_workspace.tools.core import workspace_info
from soliplex_workspace.tools.core import workspace_list

from .conftest import requires_dufs


@requires_dufs
class TestWorkspaceCleanup:
    async def test_audit_and_delete_largest(self, workspace):
        p, rid = workspace

        # Upload mix of small and large files
        await p.upload_file(rid, "/small.txt", b"tiny")
        await p.upload_file(rid, "/medium.csv", b"x" * 500)
        await p.upload_file(rid, "/large.bin", b"x" * 2000)

        # Full inventory
        tree = await workspace_list(p, rid, recursive=True)
        assert len(tree.files) == 3

        # Inspect each file
        sizes = {}
        for f in tree.files:
            info = await workspace_info(p, rid, f.path)
            sizes[info.path] = info.size_bytes

        # Verify size ordering
        assert sizes["/large.bin"] > sizes["/medium.csv"]
        assert sizes["/medium.csv"] > sizes["/small.txt"]

        # Delete the largest
        result = await workspace_delete(p, rid, "/large.bin")
        assert result.ok is True

        # Verify gone
        after = await workspace_list(p, rid, recursive=True)
        paths = [f.path for f in after.files]
        assert "/large.bin" not in paths
        assert "/small.txt" in paths
        assert "/medium.csv" in paths
