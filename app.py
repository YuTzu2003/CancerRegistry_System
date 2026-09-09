import os
from flask import session
from modules.application import create_app
from modules.server import run_server

app, APP_ENV, APP_DEBUG = create_app()

@app.context_processor
def inject_nav():
    nav_items = [
        {"title": "資料審核", "icon": "bi-funnel", "subitems": [
            {"endpoint": "clean.clean", "title": "資料清洗", "icon": "bi-play-circle"},
            {"endpoint": "history.history", "title": "資料審核紀錄", "icon": "bi-file-earmark-text"},
        ]},
        {"endpoint": "data_gen.dataGen", "title": "虛擬資料生成", "icon": "bi-database-add"},
        {"endpoint": "key_application.application", "title": "權限申請", "icon": "bi-key"},
        {"title": "報表分析", "icon": "bi-bar-chart", "subitems": [
            {"endpoint": "dashboard.dashboard", "title": "年報分析", "icon": "bi-bar-chart"},
            {"endpoint": "dashboard.compare", "title": "年度比較", "icon": "bi-columns-gap"},
            {"endpoint": "auth.data_update_access", "title": "資料維護", "icon": "bi-database-gear"},
        ]},
    ]
    if session.get("position") == "Admin":
        nav_items.append({"title": "權限管理", "icon": "bi-shield-lock", "subitems": [
            {"endpoint": "member.member", "title": "使用者管理", "icon": "bi-people"},
            {"endpoint": "key_approval.key_approval", "title": "金鑰申請審核", "icon": "bi-key-fill"},
        ]})

    provider = os.environ.get("LLM_PROVIDER")
    model = os.environ.get("OPENAI_MODEL") if provider and provider.lower() == "openai" else os.environ.get("LLM_MODEL")
    return {"nav_items": nav_items, "llm_provider": provider, "llm_model": model}


if __name__ == "__main__":
    run_server(app, APP_ENV, APP_DEBUG)