import atexit
import logging
from datetime import datetime
from apscheduler.events import EVENT_JOB_MISSED
from apscheduler.schedulers.background import BackgroundScheduler
from modules.config import BaseConfig
from modules.services.database_backup import run_database_backup
from modules.services.home import refresh_twcr_updates
from modules.services.audit import cleanup_expired_audit_logs
from modules.services.dashboard import cleanup_all_export_drafts
from modules.blueprint.dashboard.export_tasks import cleanup_expired_export_tasks
from modules.blueprint.dashboard.llm_tasks import cleanup_expired_llm_tasks
from modules.blueprint.clean import cleanup_expired_review_records

def is_scheduler_leader(app_debug):
    if app_debug:
        return BaseConfig.WERKZEUG_RUN_MAIN
    return BaseConfig.WAITRESS_PORT == BaseConfig.BACKEND_BASE_PORT

def start_system_scheduler():
    scheduler = BackgroundScheduler()
    def log_missed_run(event):
        logging.warning("Scheduler missed job %s at %s", event.job_id, event.scheduled_run_time)
    scheduler.add_listener(log_missed_run, EVENT_JOB_MISSED)
    scheduler.add_job(refresh_twcr_updates, "cron", hour=3, minute=0, id="home_updates", replace_existing=True)
    scheduler.add_job(refresh_twcr_updates, "date", run_date=datetime.now(), id="home_updates_startup", replace_existing=True)
    scheduler.add_job(run_database_backup, "cron", hour=2, minute=0, id="database_backup", replace_existing=True)
    scheduler.add_job(cleanup_expired_review_records, "cron", hour=0, minute=0, id="review_record_cleanup", replace_existing=True)
    scheduler.add_job(cleanup_expired_audit_logs, "cron", hour=0, minute=10, id="audit_log_cleanup", replace_existing=True)
    # Export drafts (1h TTL) are only swept for the acting user on request; sweep
    # every owner's expired drafts hourly so abandoned ones don't accumulate.
    scheduler.add_job(cleanup_all_export_drafts, "cron", minute=30, id="export_draft_cleanup", replace_existing=True)
    # Remove finished background-export jobs (row + rendered files) past their TTL.
    scheduler.add_job(cleanup_expired_export_tasks, "cron", hour=1, minute=30, id="export_task_cleanup", replace_existing=True)
    # Remove finished LLM analysis tasks (row + files) past their retention window;
    # annual_report records are kept indefinitely (LLM_TASK_RETENTION_DAYS, default 1).
    scheduler.add_job(cleanup_expired_llm_tasks, "cron", hour=1, minute=45, id="llm_task_cleanup", replace_existing=True)
    scheduler.start()

    def shutdown_scheduler():
        if scheduler.running:
            scheduler.shutdown(wait=False)

    atexit.register(shutdown_scheduler)
    return scheduler
