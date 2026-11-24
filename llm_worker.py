import logging
import os
import subprocess
import sys
from modules.blueprint.dashboard.llm_tasks import run_worker
from modules.config import BaseConfig

def start_dashboard_llm_worker():
    project_root = os.path.dirname(__file__)
    count = BaseConfig.LLM_WORKERS or 1
    workers = []
    for index in range(count):
        env = os.environ.copy()
        env["LLM_WORKER_NUMBER"] = str(index + 1)
        workers.append(subprocess.Popen([sys.executable, __file__], cwd=project_root, env=env))
    return workers

def stop_dashboard_llm_worker(workers):
    for worker in workers or []:
        if worker is None or worker.poll() is not None:
            continue
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
