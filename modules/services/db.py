from sqlalchemy import create_engine
from modules.config import BaseConfig

_engine = None

# Connection-pool starting points (tune against an isolated load test before
# raising). Per process the pool holds up to pool_size persistent connections
# and may briefly open up to max_overflow more, so each process can use up to
# (pool_size + max_overflow) = 20 connections. The deployment runs
# APP_WORKERS + LLM_WORKERS separate processes, so size the SQL Server
# max connections for:
#   (APP_WORKERS + LLM_WORKERS) * (POOL_SIZE + MAX_OVERFLOW) + a few extra
# (backup uses its own non-pooled autocommit connection; see database_backup).
POOL_SIZE = 10
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30      # seconds a caller waits for a free connection
POOL_RECYCLE = 1800    # recycle idle connections after 30 min (avoids stale sockets)


def get_engine():
    global _engine
    if _engine is None:
        db_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        if not db_uri:
            raise ValueError("環境變數 SQLALCHEMY_DATABASE_URI 未設定")
        _engine = create_engine(
            db_uri,
            pool_size=POOL_SIZE,
            max_overflow=MAX_OVERFLOW,
            pool_timeout=POOL_TIMEOUT,
            pool_recycle=POOL_RECYCLE,
            pool_pre_ping=True,
        )
    return _engine

def get_conn():
    return get_engine().raw_connection()