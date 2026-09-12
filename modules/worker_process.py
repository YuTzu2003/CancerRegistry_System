"""Lifecycle helpers for the dashboard LLM worker."""
from __future__ import annotations

import logging
import os
from pathlib import Path
import subprocess
import sys


def start_llm_worker(project_root: Path) -> subprocess.Popen:
    worker_script = project_root / "run_llm_worker.py"
    process = subprocess.Popen([sys.executable, str(worker_script)], cwd=project_root)
    logging.info("LLM worker started with PID %s", process.pid)
    return process


def stop_llm_worker(process: subprocess.Popen | None) -> None:
    if not process or process.poll() is not None:
        return
    logging.info("Stopping LLM worker with PID %s", process.pid)
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False, capture_output=True)
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()