import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from modules.services import home


class HomeAnnouncementTests(unittest.TestCase):
    def test_homepage_reads_saved_announcements_without_fetching_the_network(self):
        saved_updates = {"latest": [{"title": "saved"}], "downloads": []}
        with TemporaryDirectory() as directory:
            updates_file = Path(directory) / "twcr_updates.json"
            updates_file.write_text(json.dumps(saved_updates), encoding="utf-8")
            with patch.object(home, "TWCR_UPDATES_FILE", updates_file):
                with patch.object(home, "_fetch_twcr_source") as fetch_source:
                    result = home.fetch_twcr_updates()

        self.assertEqual(result, saved_updates)
        fetch_source.assert_not_called()

    def test_daily_update_saves_downloaded_announcements(self):
        with TemporaryDirectory() as directory:
            updates_file = Path(directory) / "twcr_updates.json"
            with patch.object(home, "TWCR_UPDATES_FILE", updates_file):
                with patch.object(home, "_fetch_twcr_source", return_value=[{"title": "item"}]):
                    with patch.object(home, "write_audit_log") as write_audit_log:
                        home.refresh_twcr_updates()

            saved_updates = json.loads(updates_file.read_text(encoding="utf-8"))

        self.assertEqual(saved_updates["latest"], [])
        self.assertEqual(saved_updates["downloads"], [{"title": "item"}])
        write_audit_log.assert_called_once_with(
            "system_home_updates_auto",
            {"execution_mode": "system_automatic", "latest_count": 0, "downloads_count": 1},
            user_id="SYSTEM",
        )


if __name__ == "__main__":
    unittest.main()
