from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

from modules import worker_process


class WorkerProcessTests(unittest.TestCase):
    def test_start_uses_current_python_and_project_working_directory(self):
        process = Mock(pid=123)
        with patch.object(worker_process.subprocess, "Popen", return_value=process) as popen:
            with patch.object(worker_process.sys, "executable", "python"):
                result = worker_process.start_llm_worker(Path("C:/project"))
        self.assertIs(result, process)
        popen.assert_called_once_with(["python", str(Path("C:/project") / "run_llm_worker.py")], cwd=Path("C:/project"))

    def test_windows_stop_terminates_the_worker_process_tree(self):
        process = Mock(pid=123)
        process.poll.return_value = None
        with patch.object(worker_process.os, "name", "nt"):
            with patch.object(worker_process.subprocess, "run") as run:
                worker_process.stop_llm_worker(process)
        run.assert_called_once_with(["taskkill", "/PID", "123", "/T", "/F"], check=False, capture_output=True)

    def test_finished_worker_is_not_stopped_again(self):
        process = Mock()
        process.poll.return_value = 0
        with patch.object(worker_process.subprocess, "run") as run:
            worker_process.stop_llm_worker(process)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()