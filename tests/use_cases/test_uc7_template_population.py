"""UC7: Template Population — search → read → write → info."""

from __future__ import annotations

import pytest

from soliplex_workspace.exceptions import WorkspaceAlreadyExistsError
from soliplex_workspace.tools.core import workspace_find
from soliplex_workspace.tools.core import workspace_info
from soliplex_workspace.tools.core import workspace_read
from soliplex_workspace.tools.core import workspace_write

from .conftest import requires_dufs


@requires_dufs
class TestTemplatePopulation:
    async def test_find_template_fill_and_save(self, workspace):
        p, rid = workspace

        # Upload template
        template = (
            "# Meeting: {{date}}\n\n"
            "## Attendees\n- {{attendees}}\n\n"
            "## Notes\n{{notes}}\n"
        )
        await p.create_folder(rid, "/templates")
        await p.upload_file(
            rid, "/templates/meeting_template.md", template.encode()
        )

        # Search for template (also matches "templates" dir)
        search = await workspace_find(p, rid, "*template*")
        assert search.total >= 1
        file_matches = [m for m in search.matches if not m.is_directory]
        assert len(file_matches) == 1
        assert file_matches[0].name == "meeting_template.md"

        # Read template
        tmpl = await workspace_read(p, rid, "/templates/meeting_template.md")
        assert "{{date}}" in tmpl.content

        # Fill template
        filled = tmpl.content.replace("{{date}}", "2025-02-24")
        filled = filled.replace("{{attendees}}", "Alice, Bob")
        filled = filled.replace("{{notes}}", "Discussed roadmap.")

        # Write filled meeting notes
        await p.create_folder(rid, "/meetings")
        w = await workspace_write(p, rid, "/meetings/2025-02-24.md", filled)
        assert w.size_bytes > 0

        # Verify via info
        info = await workspace_info(p, rid, "/meetings/2025-02-24.md")
        assert info.size_bytes == w.size_bytes

        # Verify overwrite=False protection
        with pytest.raises(WorkspaceAlreadyExistsError):
            await workspace_write(
                p, rid, "/meetings/2025-02-24.md", "overwrite!"
            )

        # Overwrite=True succeeds
        w2 = await workspace_write(
            p,
            rid,
            "/meetings/2025-02-24.md",
            "Updated notes.",
            overwrite=True,
        )
        assert w2.size_bytes > 0
