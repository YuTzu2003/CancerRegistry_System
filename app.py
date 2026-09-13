import atexit
from llm_worker import start_dashboard_llm_worker, stop_dashboard_llm_worker
from modules.application import create_app, should_start_background_worker
from modules.schedule import is_scheduler_leader, start_system_scheduler
from modules.server import run_server

app, APP_ENV, APP_DEBUG = create_app()

if __name__ == "__main__":
    worker = None
    scheduler = None
    if should_start_background_worker(APP_DEBUG):
        worker = start_dashboard_llm_worker()
        atexit.register(stop_dashboard_llm_worker, worker)
    if is_scheduler_leader(APP_DEBUG):
        scheduler = start_system_scheduler()
    try:
        run_server(app, APP_ENV, APP_DEBUG)
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
        stop_dashboard_llm_worker(worker)