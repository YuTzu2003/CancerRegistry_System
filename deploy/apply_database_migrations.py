"""Apply idempotent schema updates required by an existing installation."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

from init_database import GO_SEPARATOR, MIGRATION_PATHS, read_sql


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    database_uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if not database_uri:
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is required in .env")

    engine = create_engine(database_uri, pool_pre_ping=True)
    with engine.begin() as connection:
        for migration_path in MIGRATION_PATHS:
            for batch in (item.strip() for item in GO_SEPARATOR.split(read_sql(migration_path)) if item.strip()):
                connection.exec_driver_sql(batch)
            print(f"Applied database migration: {migration_path.name}.")


if __name__ == "__main__":
    main()
