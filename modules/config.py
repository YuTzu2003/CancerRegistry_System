import os
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

def _required_env(name):
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment setting: {name}")
    return value

def _parse_int(value, name):
    try:
        return int(value)
    except ValueError as error:
        raise RuntimeError(f"Environment setting {name} must be an integer") from error

def _optional_int(name):
    value = os.getenv(name)
    return _parse_int(value, name) if value and value.strip() else None

def parse_bool(value, default=False):
    if value is None:
        return default
    text = str(value).strip().lower()
    return default if not text else text in {"1", "true", "yes", "on"}

class BaseConfig:
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    APP_ENV = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "development").strip().lower()
    APP_DEBUG = parse_bool(os.getenv("APP_DEBUG"), APP_ENV == "development")
    SECRET_KEY = _required_env("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _required_env("SQLALCHEMY_DATABASE_URI")

    SESSION_COOKIE_SECURE = parse_bool(_required_env("SESSION_COOKIE_SECURE"))
    SESSION_COOKIE_SAMESITE = _required_env("SESSION_COOKIE_SAMESITE")
    SESSION_LIFETIME_SECONDS = _parse_int(_required_env("SESSION_LIFETIME_SECONDS"), "SESSION_LIFETIME_SECONDS")
    MAX_UPLOAD_MB = 50
    LOGIN_MAX_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW_SECONDS = 900
    MAX_CONTENT_LENGTH = MAX_UPLOAD_MB * 1024 * 1024

    FLASK_HOST = _required_env("FLASK_HOST")
    FLASK_PORT = _parse_int(_required_env("FLASK_PORT"), "FLASK_PORT")
    BACKEND_BASE_PORT = _optional_int("BACKEND_BASE_PORT")
    WAITRESS_HOST = os.getenv("WAITRESS_HOST")
    WAITRESS_PORT = _optional_int("WAITRESS_PORT")
    WAITRESS_THREADS = _optional_int("WAITRESS_THREADS")
    WAITRESS_BACKLOG = _optional_int("WAITRESS_BACKLOG")
    WAITRESS_CONNECTION_LIMIT = _optional_int("WAITRESS_CONNECTION_LIMIT")
    WAITRESS_CHANNEL_TIMEOUT = _optional_int("WAITRESS_CHANNEL_TIMEOUT")
    TRUSTED_PROXY = os.getenv("TRUSTED_PROXY")
    PROXY_COUNT = _optional_int("PROXY_COUNT")

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    LLM_BASE_URL = os.getenv("LLM_BASE_URL")
    LLM_API_KEY = os.getenv("LLM_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
    LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "180"))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "").strip()
    WERKZEUG_RUN_MAIN = os.getenv("WERKZEUG_RUN_MAIN") == "true"
    TESTING = False

    @classmethod
    def validate_production_server(cls):
        required = (
            "BACKEND_BASE_PORT", "WAITRESS_HOST", "WAITRESS_PORT", "WAITRESS_THREADS",
            "WAITRESS_BACKLOG", "WAITRESS_CONNECTION_LIMIT", "WAITRESS_CHANNEL_TIMEOUT",
            "TRUSTED_PROXY", "PROXY_COUNT",
        )
        missing = [name for name in required if getattr(cls, name) is None]
        if missing:
            raise RuntimeError(f"Missing required production environment settings: {', '.join(missing)}")

class TestingConfig(BaseConfig):
    APP_ENV = "testing"
    APP_DEBUG = False
    TESTING = True

class DevelopmentConfig(BaseConfig):
    APP_ENV = "development"

class ProductionConfig(BaseConfig):
    APP_ENV = "production"
    APP_DEBUG = False
    SESSION_COOKIE_SECURE = parse_bool(os.getenv("SESSION_COOKIE_SECURE"), True)


CONFIG_BY_NAME = {
     None: BaseConfig,
    "default": BaseConfig,
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def test_settings():
    from modules.services.database_backup import BACKUP_DIRECTORY
    from modules.services.db import get_conn
    from modules.services.llm_service import get_llm_client

    results = {}
    connection = None
    probe_path = None
    try:
        connection = get_conn()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        results["資料庫"] = None
    except Exception as error:
        results["資料庫"] = str(error)
    finally:
        if connection:
            connection.close()
    try:
        client, _ = get_llm_client()
        client.models.list()
        results["LLM"] = None
    except Exception as error:
        results["LLM"] = str(error)
    try:
        BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
        probe_path = BACKUP_DIRECTORY / f".config-check-{uuid4().hex}"
        probe_path.write_text("ok", encoding="utf-8")
        results["備份目錄"] = None
    except Exception as error:
        results["備份目錄"] = str(error)
    finally:
        if probe_path:
            probe_path.unlink(missing_ok=True)
    return results

if __name__ == "__main__":
    results = test_settings()
    failures = {name: error for name, error in results.items() if error}
    for name, error in results.items():
        print(f"{'FAIL' if error else 'OK'}  {name}{': ' + error if error else ''}")
    if failures:
        raise SystemExit(1)
