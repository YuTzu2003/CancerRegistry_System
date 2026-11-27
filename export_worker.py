import logging
import os
import subprocess
import sys
from modules.blueprint.dashboard.export_tasks import run_export_worker


def _export_worker_count():
    """Number of export workers to spawn (EXPORT_WORKERS, optional, default 1)."""
    raw = os.environ.get("EXPORT_WORKERS")
    if raw and raw.strip():
        try:
            return max(1, min(8, int(raw)))
        except ValueError:
            pass
    return 1


def start_dashboard_export_worker():
    """Spawn the export worker process(es) as children of the running app.

    Mirrors start_dashboard_llm_worker: used only when the app auto-starts
    background workers (development; see should_start_background_worker). In
    production the workers run as their own scheduled tasks instead.
    """
    project_root = os.path.dirname(__file__)
    workers = []
    for index in range(_export_worker_count()):
        env = os.environ.copy()
        env["EXPORT_WORKER_NUMBER"] = str(index + 1)
        workers.append(subprocess.Popen([sys.executable, __file__], cwd=project_root, env=env))
    return workers


def stop_dashboard_export_worker(workers):
    for worker in workers or []:
        if worker is None or worker.poll() is not None:
            continue
        worker.terminate()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s",datefmt="%Y-%m-%d %H:%M:%S",stream=sys.stdout,)
    logging.info("Export worker process started")
    run_export_worker()