import atexit
from datetime import datetime
import os
import subprocess
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from flask import session
from modules.application import create_app
from modules.config import get_int_env
from modules.services.database_backup import run_database_backup
from modules.services.home import refresh_twcr_updates
from modules.server import run_server

app, APP_ENV, APP_DEBUG = create_app()

def start_dashboard_llm_worker():
    project_root = os.path.dirname(__file__)
    worker_script = os.path.join(project_root, "llm_worker.py")
    return subprocess.Popen([sys.executable, worker_script], cwd=project_root)

def stop_dashboard_llm_worker(worker):
    if worker is None or worker.poll() is not None:
        return
    worker.terminate()
    try:
        worker.wait(timeout=10)
    except subprocess.TimeoutExpired:
        worker.kill()

def is_scheduler_leader():
    if APP_DEBUG:
        return os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    return str(os.environ.get("WAITRESS_PORT", "")) == str(get_int_env("BACKEND_BASE_PORT"))

def start_system_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_twcr_updates, "cron", hour=3, minute=0, id="home_updates", replace_existing=True)
    scheduler.add_job(refresh_twcr_updates, "date", run_date=datetime.now(), id="home_updates_startup", replace_existing=True)
    scheduler.add_job(run_database_backup, "cron", hour=2, minute=0, id="database_backup", replace_existing=True)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))
    return scheduler

@app.context_processor
def inject_nav():
    nav_items = [
        {"title": "資料審核", "icon": "bi-funnel", "subitems": [
            {"endpoint": "clean.clean", "title": "資料清洗", "icon": "bi-play-circle"},
            {"endpoint": "clean.history", "title": "資料審核紀錄", "icon": "bi-file-earmark-text"},
        ]},
        {"title": "報表分析", "icon": "bi-bar-chart", "subitems": [
            {"endpoint": "dashboard.dashboard", "title": "年報分析", "icon": "bi-bar-chart"},
            {"endpoint": "dashboard.compare", "title": "年度比較", "icon": "bi-columns-gap"},
            {"endpoint": "auth.data_update_access", "title": "資料維護", "icon": "bi-database-gear"},
        ]},
        {"endpoint": "data_gen.dataGen", "title": "虛擬資料生成", "icon": "bi-database-add"},      
        {"endpoint": "indicators.indicators", "title": "監測指標", "icon": "bi-clipboard2-pulse"},
        {"endpoint": "key_application.application", "title": "權限申請", "icon": "bi-key"},      
    ]
    if session.get("position") == "Admin":
        nav_items.append({"title": "權限管理", "icon": "bi-shield-lock", "subitems": [
            {"endpoint": "member.member", "title": "使用者管理", "icon": "bi-people"},
            {"endpoint": "key_approval.key_approval", "title": "金鑰申請審核", "icon": "bi-key-fill"},
            {"endpoint": "audit_logs.audit_logs", "title": "系統操作日誌", "icon": "bi-journal-text"},]})

    provider = os.environ.get("LLM_PROVIDER")
    model = os.environ.get("OPENAI_MODEL") if provider and provider.lower() == "openai" else os.environ.get("LLM_MODEL")
    return {"nav_items": nav_items, "llm_provider": provider, "llm_model": model}

if __name__ == "__main__":
    worker = None
    scheduler = None
    should_start_worker = not APP_DEBUG or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if should_start_worker:
        worker = start_dashboard_llm_worker()
        atexit.register(stop_dashboard_llm_worker, worker)
    if is_scheduler_leader():
        scheduler = start_system_scheduler()
    try:
        run_server(app, APP_ENV, APP_DEBUG)
    finally:
        if scheduler:
            scheduler.shutdown(wait=False)
        stop_dashboard_llm_worker(worker)
