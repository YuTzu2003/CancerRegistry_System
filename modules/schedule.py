import atexit
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from modules.config import BaseConfig
from modules.services.database_backup import run_database_backup
from modules.services.home import refresh_twcr_updates

def is_scheduler_leader(app_debug):
    if app_debug:
        return BaseConfig.WERKZEUG_RUN_MAIN
    return BaseConfig.WAITRESS_PORT == BaseConfig.BACKEND_BASE_PORT

def start_system_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_twcr_updates, "cron", hour=3, minute=0, id="home_updates", replace_existing=True)
    scheduler.add_job(refresh_twcr_updates, "date", run_date=datetime.now(), id="home_updates_startup", replace_existing=True)
    scheduler.add_job(run_database_backup, "cron", hour=2, minute=0, id="database_backup", replace_existing=True)
    scheduler.start()

    def shutdown_scheduler():
        """Flask reloader may already have stopped this scheduler at exit."""
        if scheduler.running:
            scheduler.shutdown(wait=False)

    atexit.register(shutdown_scheduler)
    return scheduler
