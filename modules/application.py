import logging
import os
import sys
from datetime import timedelta

import jinja2
from dotenv import load_dotenv
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from modules.blueprint.admin.key_approval import key_approval_bp
from modules.blueprint.admin.member import member_bp
from modules.blueprint.auth.key_application import key_application_bp
from modules.services.home import register_main_routes
from modules.config import get_env, get_int_env
from modules.services import auth_bp, clean_bp, dashboard_bp, data_gen_bp, login_required

import modules.blueprint.auth.histology_code
import modules.blueprint.auth.key_access
import modules.blueprint.auth.national_import


def create_app():
    load_dotenv()
    app_env = get_env("APP_ENV").strip().lower()
    if app_env not in {"development", "production"}:
        raise RuntimeError("APP_ENV must be development or production")

    app_debug = get_env("APP_DEBUG").strip().lower() in {"1", "true", "yes", "on"}
    if app_env == "production":
        app_debug = False

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S", handlers=[logging.StreamHandler(sys.stdout)])
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.handlers = []
    werkzeug_logger.propagate = True

    project_root = os.path.dirname(os.path.dirname(__file__))
    app = Flask(__name__, static_folder=os.path.join(project_root, "static"))
    app.jinja_loader = jinja2.ChoiceLoader([jinja2.FileSystemLoader(os.path.join(project_root, "modules", "blueprint", "templates")), jinja2.FileSystemLoader(os.path.join(project_root, "templates"))])
    secret_key = get_env("SECRET_KEY")
    if app_env == "production" and (len(secret_key) < 32 or secret_key == "development-only-change-before-production"):
        raise RuntimeError("Production SECRET_KEY must contain at least 32 characters")
    app.secret_key = secret_key
    app.config.update(PERMANENT_SESSION_LIFETIME=timedelta(seconds=get_int_env("SESSION_LIFETIME_SECONDS")), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE=get_env("SESSION_COOKIE_SAMESITE"), SESSION_COOKIE_SECURE=get_env("SESSION_COOKIE_SECURE").lower() == "true")
    if app_env == "production":
        proxy_count = get_int_env("PROXY_COUNT")
        if proxy_count != 1:
            raise RuntimeError("PROXY_COUNT must be 1 in production")
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_count, x_proto=proxy_count, x_host=proxy_count, x_port=proxy_count)

    for blueprint in (auth_bp, member_bp, clean_bp, data_gen_bp, dashboard_bp, key_application_bp, key_approval_bp):
        app.register_blueprint(blueprint)
    register_main_routes(app, app_env, login_required)

    base_dir = os.path.dirname(os.path.dirname(__file__))
    os.makedirs("tasks/Jobs", exist_ok=True)
    os.makedirs(os.path.join(project_root, "tasks", "data"), exist_ok=True)
    return app, app_env, app_debug
