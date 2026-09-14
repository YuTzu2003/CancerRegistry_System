import os
import re
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "deploy" / "database" / "CancerRegistry_System.sql"
GO_SEPARATOR = re.compile(r"(?im)^\s*GO\s*(?:--.*)?$")
FORBIDDEN_STATEMENTS = re.compile(r"(?im)^\s*(?:USE|CREATE\s+DATABASE|ALTER\s+DATABASE)\b")


def read_sql(path: Path) -> str:
    content = path.read_bytes()
    if content.startswith(b"\xff\xfe"):
        return content.decode("utf-16")
    if content.startswith(b"\xfe\xff"):
        return content.decode("utf-16-be")
    return content.decode("utf-8-sig")


def load_sql_batches() -> tuple[str, ...]:
    if not SCHEMA_PATH.exists():
        raise RuntimeError(f"Database schema file was not found: {SCHEMA_PATH}")

    schema = read_sql(SCHEMA_PATH)
    if FORBIDDEN_STATEMENTS.search(schema):
        raise RuntimeError("CancerRegistry_System.sql must not select or create a database; configure SQLALCHEMY_DATABASE_URI in .env instead.")

    batches = tuple(batch.strip() for batch in GO_SEPARATOR.split(schema) if batch.strip())
    if not batches:
        raise RuntimeError("Database schema file does not contain executable SQL.")
    return batches


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    database_uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not database_uri:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is required in .env")

    engine = create_engine(database_uri, pool_pre_ping=True)
    with engine.begin() as connection:
        existing_table = connection.exec_driver_sql("SELECT TOP 1 name FROM sys.tables WHERE is_ms_shipped = 0").scalar()
        if existing_table:
            raise RuntimeError(f"Database is not empty (found table: {existing_table}). Database initialization only supports a new database.")
        for index, batch in enumerate(load_sql_batches(), start=1):
            connection.exec_driver_sql(batch)
            print(f"Executed SQL batch {index}.")
    print("Database schema initialization completed.")


if __name__ == "__main__":
    main()