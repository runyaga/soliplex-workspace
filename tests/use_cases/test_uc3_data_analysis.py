"""UC3: Data Analysis Report — list → read → write → info."""

from __future__ import annotations

from soliplex_workspace.tools.core import workspace_info
from soliplex_workspace.tools.core import workspace_list
from soliplex_workspace.tools.core import workspace_read
from soliplex_workspace.tools.core import workspace_write

from .conftest import requires_dufs


@requires_dufs
class TestDataAnalysis:
    async def test_analyze_csv_write_report(self, workspace):
        p, rid = workspace

        # Upload CSV data
        csv_data = "product,sales,region\nWidget,100,East\nGadget,250,West\n"
        await p.create_folder(rid, "/data")
        await p.upload_file(rid, "/data/sales.csv", csv_data.encode())

        # List data directory
        listing = await workspace_list(p, rid, path="/data")
        assert len(listing.files) == 1
        assert listing.files[0].name == "sales.csv"

        # Read CSV
        csv = await workspace_read(p, rid, "/data/sales.csv")
        assert "Widget" in csv.content
        assert "Gadget" in csv.content

        # Write analysis report
        report = (
            "# Sales Analysis\n\n"
            "- Widget: 100 units (East)\n"
            "- Gadget: 250 units (West)\n"
            "- Total: 350 units\n"
        )
        await p.create_folder(rid, "/reports")
        w = await workspace_write(p, rid, "/reports/analysis.md", report)
        assert w.size_bytes > 0

        # Verify via info
        info = await workspace_info(p, rid, "/reports/analysis.md")
        assert info.size_bytes == w.size_bytes
        assert info.is_directory is False
