from modules.application import create_app
from modules.schedule import is_scheduler_leader, start_system_scheduler
from modules.server import run_server

app, APP_ENV, APP_DEBUG = create_app()

if __name__ == "__main__":
    scheduler = None
    if is_scheduler_leader(APP_DEBUG):
        scheduler = start_system_scheduler()
    try:
        run_server(app, APP_ENV, APP_DEBUG)
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
