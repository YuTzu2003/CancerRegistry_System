from sqlalchemy import create_engine
from modules.config import BaseConfig

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        db_uri = BaseConfig.SQLALCHEMY_DATABASE_URI
        if not db_uri:
            raise ValueError("環境變數 SQLALCHEMY_DATABASE_URI 未設定")
        _engine = create_engine(db_uri, pool_pre_ping=True)
    return _engine

def get_conn():
    return get_engine().raw_connection()