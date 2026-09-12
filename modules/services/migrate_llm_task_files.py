"""Move existing LLM task payloads from SQL Server into task.json files."""
from __future__ import annotations

import json
import shutil

from modules.services.db import get_conn
from modules.services.llm_tasks import TASK_ROOT, _dir, _write_task_data


def migrate_llm_task_files():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT TaskID,TaskType,ProgressCurrent,PayloadJson FROM dbo.LLMTaskWorker')
        tasks = cursor.fetchall()
    finally:
        conn.close()

    for task_id, task_type, progress_current, payload_json in tasks:
        task_id = str(task_id)
        old_directory = TASK_ROOT / task_id
        task_directory = _dir(task_type, task_id)
        if old_directory.exists() and not task_directory.exists():
            task_directory.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old_directory), str(task_directory))
        _write_task_data(task_type, task_id, {
            'PayloadJson': json.loads(payload_json or '{}'),
            'ProgressCurrent': progress_current,
        })
    return len(tasks)


if __name__ == '__main__':
    print(f'Migrated {migrate_llm_task_files()} LLM task(s).')
