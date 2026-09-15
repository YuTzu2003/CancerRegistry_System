import logging
import os
import subprocess
import sys
from modules.blueprint.dashboard.llm_tasks import run_worker

def start_dashboard_llm_worker():
    project_root = os.path.dirname(__file__)
    return subprocess.Popen([sys.executable, __file__], cwd=project_root)

def stop_dashboard_llm_worker(worker):
    if worker is None or worker.poll() is not None:
        return
    worker.terminate()
    try:
        worker.wait(timeout=10)
    except subprocess.TimeoutExpired:
        worker.kill()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    logging.info("LLM worker process started")
    run_worker()
