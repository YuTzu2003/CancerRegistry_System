from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from modules.services import dashboard
from modules.blueprint.dashboard import chart_analytics


class DashboardStorageTests(unittest.TestCase):
    def test_new_dashboard_upload_path_uses_tasks_dashboard(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(dashboard, "DASHBOARD_DATA", str(root / "dashboard")):
                path = dashboard._absolute_dashboard_path(
                    dashboard._dashboard_storage_path("file-id", "source.xlsx")
                )

        self.assertEqual(path, str(root / "dashboard" / "file-id" / "source.xlsx"))

    def test_existing_dashboard_paths_can_still_read_legacy_files(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            legacy_file = root / "data" / "dashboard" / "file-id" / "source.xlsx"
            legacy_file.parent.mkdir(parents=True)
            legacy_file.write_text("legacy", encoding="utf-8")
            with (
                patch.object(dashboard, "DASHBOARD_DATA", str(root / "dashboard")),
                patch.object(dashboard, "LEGACY_DASHBOARD_DATA", str(root / "data" / "dashboard")),
                patch.object(chart_analytics, "DASHBOARD_DATA", str(root / "dashboard")),
                patch.object(chart_analytics, "LEGACY_DASHBOARD_DATA", str(root / "data" / "dashboard")),
            ):
                self.assertEqual(dashboard._absolute_dashboard_path("dashboard/file-id/source.xlsx"), str(legacy_file))
                self.assertEqual(chart_analytics._safe_dashboard_path("dashboard/file-id/source.xlsx"), str(legacy_file))


if __name__ == "__main__":
    unittest.main()
