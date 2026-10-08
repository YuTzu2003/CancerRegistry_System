from modules.application import create_app, should_start_background_worker
from modules.schedule import is_scheduler_leader, start_system_scheduler
from modules.server import run_server
from llm_worker import start_dashboard_llm_worker, stop_dashboard_llm_worker

app, APP_ENV, APP_DEBUG = create_app()

if __name__ == "__main__":
    scheduler = None
    llm_worker = None
    if is_scheduler_leader(APP_DEBUG):
        scheduler = start_system_scheduler()
    if should_start_background_worker(APP_DEBUG):
        llm_worker = start_dashboard_llm_worker()
    try:
        run_server(app, APP_ENV, APP_DEBUG)
    finally:
        stop_dashboard_llm_worker(llm_worker)
        if scheduler:
            scheduler.shutdown(wait=False)
