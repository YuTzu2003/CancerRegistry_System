from datetime import timedelta
import logging
import os
import sys
import jinja2
from flask import Flask, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix
from modules.blueprint.admin.audit_logs import audit_logs_bp
from modules.blueprint.admin.key_approval import key_approval_bp
from modules.blueprint.admin.member import member_bp
from modules.blueprint.auth.key_application import key_application_bp
from modules.config import BaseConfig, CONFIG_BY_NAME
from modules.services import auth_bp, clean_bp, dashboard_bp, data_gen_bp, indicators_bp, login_required
from modules.services.audit import register_audit_logging
from modules.services.home import register_main_routes
import modules.blueprint.auth.histology_code
import modules.blueprint.auth.key_access
import modules.blueprint.auth.national_import

def create_app():
    runtime_config = CONFIG_BY_NAME.get(BaseConfig.APP_ENV)
    if runtime_config is None:
        raise RuntimeError("APP_ENV must be development, production, or testing")
    app_env = runtime_config.APP_ENV
    app_debug = False if app_env == "production" else runtime_config.APP_DEBUG

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S", handlers=[logging.StreamHandler(sys.stdout)])
    logging.getLogger("werkzeug").handlers = []
    logging.getLogger("werkzeug").propagate = True

    project_root = os.path.dirname(os.path.dirname(__file__))
    flask_app = Flask(__name__, static_folder=os.path.join(project_root, "static"))
    flask_app.jinja_loader = jinja2.ChoiceLoader([jinja2.FileSystemLoader(os.path.join(project_root, "modules", "blueprint", "templates")), jinja2.FileSystemLoader(os.path.join(project_root, "templates"))])
    if app_env == "production" and (len(BaseConfig.SECRET_KEY) < 32 or BaseConfig.SECRET_KEY == "development-only-change-before-production"):
        raise RuntimeError("Production SECRET_KEY must contain at least 32 characters")
    flask_app.secret_key = BaseConfig.SECRET_KEY
    flask_app.config.update(PERMANENT_SESSION_LIFETIME=timedelta(seconds=runtime_config.SESSION_LIFETIME_SECONDS), SESSION_REFRESH_EACH_REQUEST=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE=runtime_config.SESSION_COOKIE_SAMESITE, SESSION_COOKIE_SECURE=runtime_config.SESSION_COOKIE_SECURE, MAX_CONTENT_LENGTH=runtime_config.MAX_CONTENT_LENGTH, TESTING=runtime_config.TESTING)

    @flask_app.errorhandler(413)
    def request_too_large(_error):
        message = f"上傳檔案不可超過 {runtime_config.MAX_UPLOAD_MB} MB。"
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": message}), 413
        return message, 413
    
    if app_env == "production":
        if BaseConfig.PROXY_COUNT != 1:
            raise RuntimeError("PROXY_COUNT must be 1 in production")
        flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app, x_for=BaseConfig.PROXY_COUNT, x_proto=BaseConfig.PROXY_COUNT, x_host=BaseConfig.PROXY_COUNT, x_port=BaseConfig.PROXY_COUNT)

    for blueprint in (auth_bp, member_bp, audit_logs_bp, clean_bp, data_gen_bp, dashboard_bp, indicators_bp, key_application_bp, key_approval_bp):
        flask_app.register_blueprint(blueprint)
    register_main_routes(flask_app, app_env, login_required)
    register_audit_logging(flask_app)
    os.makedirs("tasks/Jobs", exist_ok=True)
    os.makedirs(os.path.join(project_root, "tasks", "data"), exist_ok=True)

    @flask_app.context_processor
    def inject_template_settings():
        model = BaseConfig.OPENAI_MODEL if BaseConfig.LLM_PROVIDER == "openai" else BaseConfig.LLM_MODEL
        return {"llm_model": model}

    return flask_app, app_env, app_debug

def should_start_background_worker(app_debug):
    return not app_debug or BaseConfig.WERKZEUG_RUN_MAIN