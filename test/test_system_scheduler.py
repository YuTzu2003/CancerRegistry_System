from pathlib import Path
from tempfile import TemporaryDirectory
import os
from datetime import datetime, timedelta
import unittest
from unittest.mock import Mock, patch

import app as application
from modules.services import database_backup


class SystemSchedulerTests(unittest.TestCase):
    def test_scheduler_registers_daily_home_and_backup_jobs(self):
        scheduler = Mock()
        with patch.object(application, "BackgroundScheduler", return_value=scheduler):
            application.start_system_scheduler()

        self.assertEqual(scheduler.add_job.call_count, 3)
        self.assertEqual(scheduler.add_job.call_args_list[0].kwargs["hour"], 3)
        self.assertEqual(scheduler.add_job.call_args_list[1].args[1], "date")
        self.assertEqual(scheduler.add_job.call_args_list[2].kwargs["hour"], 2)
        scheduler.start.assert_called_once()

    def test_dashboard_llm_worker_starts_with_the_application_python(self):
        process = Mock()
        with patch.object(application.subprocess, "Popen", return_value=process) as popen:
            with patch.object(application.sys, "executable", "python"):
                result = application.start_dashboard_llm_worker()

        self.assertIs(result, process)
        self.assertEqual(popen.call_args.args[0][0], "python")
        self.assertTrue(popen.call_args.args[0][1].endswith("llm_worker.py"))

    def test_dashboard_llm_worker_stops_cleanly(self):
        worker = Mock()
        worker.poll.return_value = None
        application.stop_dashboard_llm_worker(worker)

        worker.terminate.assert_called_once()
        worker.wait.assert_called_once_with(timeout=10)

    def test_database_backup_uses_timestamped_backup_file_and_audits_it(self):
        cursor = Mock()
        cursor.fetchone.return_value = ("CancerRegistry",)
        cursor.nextset.return_value = False
        connection = Mock()
        connection.cursor.return_value = cursor
        with TemporaryDirectory() as directory:
            expired_backup = Path(directory) / "old_back.bak"
            expired_backup.write_text("old", encoding="utf-8")
            expired_time = (datetime.now() - timedelta(days=4)).timestamp()
            os.utime(expired_backup, (expired_time, expired_time))
            with (
                patch.object(database_backup, "BACKUP_DIRECTORY", Path(directory)),
                patch.object(database_backup, "get_conn", return_value=connection),
                patch.object(database_backup, "write_audit_log") as write_audit_log,
            ):
                backup_path = database_backup.run_database_backup()

        self.assertEqual(backup_path.parent, Path(directory))
        self.assertTrue(backup_path.name.endswith("_back.bak"))
        self.assertFalse(expired_backup.exists())
        self.assertIn("BACKUP DATABASE [CancerRegistry]", cursor.execute.call_args_list[1].args[0])
        write_audit_log.assert_called_once()
        self.assertEqual(write_audit_log.call_args.args[0], "system_database_backup_auto")


if __name__ == "__main__":
    unittest.main()
