from __future__ import annotations
from datetime import datetime, timedelta
import logging
from pathlib import Path
from modules.services.audit import write_audit_log
from modules.services.db import get_conn

BACKUP_DIRECTORY = Path(__file__).resolve().parents[2] / "tasks" / "backups"

def _remove_expired_backups(now):
    cutoff = now - timedelta(days=3)
    removed = []
    for backup_path in BACKUP_DIRECTORY.glob("*.bak"):
        if backup_path.is_file() and datetime.fromtimestamp(backup_path.stat().st_mtime) < cutoff:
            backup_path.unlink()
            removed.append(backup_path.name)
    return removed

def run_database_backup():
    connection = None
    try:
        BACKUP_DIRECTORY.mkdir(parents=True, exist_ok=True)
        connection = get_conn()
        connection.autocommit = True
        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME()")
        database_name = str(cursor.fetchone()[0])
        safe_database_name = database_name.replace("]", "]]")
        backup_time = datetime.now()
        filename = f"{backup_time:%Y%m%d_%H%M%S}_back.bak"
        backup_path = BACKUP_DIRECTORY / filename
        safe_backup_path = str(backup_path).replace("'", "''")
        cursor.execute(f"BACKUP DATABASE [{safe_database_name}] TO DISK = N'{safe_backup_path}' WITH CHECKSUM, COMPRESSION")
        while cursor.nextset():
            pass
        removed_backups = _remove_expired_backups(backup_time)
        write_audit_log(
            "system_database_backup_auto",
            {
                "execution_mode": "system_automatic",
                "database": database_name,
                "backup_path": str(backup_path),
                "removed_expired_backups": removed_backups,
            },
            user_id="SYSTEM",
        )
        logging.info("Automatic database backup completed: %s", backup_path)
        return backup_path
    except Exception as exc:
        write_audit_log(
            "system_database_backup_failed",
            {"execution_mode": "system_automatic", "error": str(exc)},
            user_id="SYSTEM",
        )
        logging.exception("Automatic database backup failed")
        raise
    finally:
        if connection:
            connection.close()