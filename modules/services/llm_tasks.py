"""Background queue and JSONL history for dashboard LLM tasks."""
from __future__ import annotations

import json
import os
import shutil
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from modules.blueprint.dashboard.reply import get_chart_insight_logic, get_compare_insight_logic
from modules.services.db import get_conn


TASK_ROOT = Path(__file__).resolve().parents[2] / 'tasks' / 'llm_tasks'
SENSITIVE_KEYS = {'api_key', 'authorization', 'password', 'token', 'patient_name', 'patient_id', 'medical_record_number'}
TASK_TYPES = {'chart', 'compare', 'annual_report', 'comparison_report'}
COMPLETED_STATUSES = {'completed', 'partial_failed', 'failed'}


def _safe(value):
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items() if str(key).lower().replace('-', '_') not in SENSITIVE_KEYS}
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


def _dir(task_type, task_id):
    return TASK_ROOT / str(task_type) / str(task_id)


def get_llm_task_directory(task_type, task_id):
    return _dir(task_type, task_id)


def _task_file(task_type, task_id):
    return _dir(task_type, task_id) / 'task.json'


def _write_task_data(task_type, task_id, data):
    path = _task_file(task_type, task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, default=str, indent=2), encoding='utf-8')


def _read_task_data(task_type, task_id):
    path = _task_file(task_type, task_id)
    if not path.exists():
        return {'PayloadJson': {}, 'ProgressCurrent': 0}
    return json.loads(path.read_text(encoding='utf-8'))


def _set_progress(task_type, task_id, current):
    data = _read_task_data(task_type, task_id)
    data['ProgressCurrent'] = current
    _write_task_data(task_type, task_id, data)


def _write(task_type, task_id, filename, row):
    path = _dir(task_type, task_id) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as file:
        file.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')


def _rows(task_type, task_id, filename):
    path = _dir(task_type, task_id) / filename
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def _rewrite(task_type, task_id, filename, rows):
    path = _dir(task_type, task_id) / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, default=str) + '\n' for row in rows), encoding='utf-8')


def _row(cursor, row):
    return dict(zip([column[0] for column in cursor.description], row))


def create_llm_task(owner_id, task_type, payload):
    if task_type not in TASK_TYPES:
        raise ValueError('Unsupported LLM task type')

    task_id = str(uuid.uuid4())
    payload = _safe(payload)
    batched = task_type in {'annual_report', 'comparison_report'}
    progress_total = max(len(payload.get('items', [])), 1) if batched else 1
    _write_task_data(task_type, task_id, {'PayloadJson': payload, 'ProgressCurrent': 0})

    if batched:
        insight_type = 'chart_insight' if task_type == 'annual_report' else 'compare_insight'
        for item in payload.get('items', []):
            _write(task_type, task_id, 'input.jsonl', {
                'custom_id': item['item_id'], 'method': 'POST', 'url': '/v1/chat/completions',
                'body': {'task_type': insight_type, 'payload': item},
            })
    else:
        _write(task_type, task_id, 'input.jsonl', {
            'item_id': task_id, 'task_type': task_type, 'payload': payload,
            'created_at': datetime.now(timezone.utc).isoformat(),
        })

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO dbo.LLMTaskWorker
               (TaskID, OwnerID, TaskType, Status, ProgressTotal, CreatedAt)
               VALUES (?, ?, ?, 'queued', ?, SYSDATETIMEOFFSET())""",
            (task_id, str(owner_id), task_type, progress_total),
        )
        conn.commit()
    finally:
        conn.close()
    return {'task_id': task_id, 'status': 'queued', 'progress_current': 0, 'progress_total': progress_total}


def _task(cursor, row):
    task = _row(cursor, row)
    task_data = _read_task_data(task['TaskType'], task['TaskID'])
    payload = task_data.get('PayloadJson') or {}
    task['ProgressCurrent'] = task_data.get('ProgressCurrent', 0)
    task['DocumentLabel'] = payload.get('_document_label', '')
    task['TaskTitle'] = payload.get('job_title') or payload.get('field_key') or payload.get('analysis_item') or 'LLM 分析'
    task['result'] = _rows(task['TaskType'], task['TaskID'], 'output.jsonl')
    return task


def get_llm_task_payload(task_id, owner_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT TaskType FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?', (str(task_id), str(owner_id)))
        row = cursor.fetchone()
        return (_read_task_data(row[0], task_id).get('PayloadJson') or {}) if row else None
    finally:
        conn.close()


def get_llm_task(task_id, owner_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT TaskID,TaskType,Status,ProgressTotal,WorkerID,CreatedAt,CompletedAt '
            'FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?',
            (str(task_id), str(owner_id)),
        )
        row = cursor.fetchone()
        return _task(cursor, row) if row else None
    finally:
        conn.close()


def list_llm_tasks(owner_id, limit=50):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT TOP (?) TaskID,TaskType,Status,ProgressTotal,WorkerID,CreatedAt,CompletedAt '
            'FROM dbo.LLMTaskWorker WHERE OwnerID=? ORDER BY CreatedAt DESC',
            (min(max(int(limit), 1), 100), str(owner_id)),
        )
        return [_task(cursor, row) for row in cursor.fetchall()]
    finally:
        conn.close()


def claim_next_llm_task(worker_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """;WITH candidate AS (
                    SELECT TOP (1) * FROM dbo.LLMTaskWorker WITH (UPDLOCK, READPAST, ROWLOCK)
                    WHERE Status='queued'
                      AND NOT EXISTS (
                          SELECT 1 FROM dbo.LLMTaskWorker WITH (UPDLOCK, HOLDLOCK) WHERE Status='running'
                      )
                    ORDER BY CreatedAt
                )
                UPDATE candidate SET Status='running', WorkerID=?
                OUTPUT inserted.TaskID, inserted.TaskType;""",
            (worker_id,),
        )
        row = cursor.fetchone()
        conn.commit()
        if not row:
            return None
        task_id, task_type = str(row[0]), row[1]
        return {'task_id': task_id, 'task_type': task_type, 'payload': _read_task_data(task_type, task_id).get('PayloadJson') or {}}
    finally:
        conn.close()


def _update(task_id, status=None):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE dbo.LLMTaskWorker
               SET Status=COALESCE(?, Status),
                   CompletedAt=CASE WHEN ? IN ('completed','partial_failed','failed') THEN SYSDATETIMEOFFSET() ELSE CompletedAt END
               WHERE TaskID=?""",
            (status, status, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def process_next_llm_task(worker_id):
    task = claim_next_llm_task(worker_id)
    if not task:
        return None
    task_id, task_type = task['task_id'], task['task_type']
    try:
        if task_type in {'annual_report', 'comparison_report'}:
            retry_path = _dir(task_type, task_id) / 'retry.jsonl'
            retrying = retry_path.exists()
            requests = _rows(task_type, task_id, 'retry.jsonl' if retrying else 'input.jsonl')
            handler = get_chart_insight_logic if task_type == 'annual_report' else get_compare_insight_logic
            for request in requests:
                item = request['body']['payload']
                result = handler(item)
                output = {'custom_id': request['custom_id'], 'field_key': item.get('field_key', ''), 'result': result}
                if retrying:
                    _rewrite(task_type, task_id, 'output.jsonl', [
                        row for row in _rows(task_type, task_id, 'output.jsonl') if row.get('custom_id') != request['custom_id']
                    ] + [output])
                else:
                    _write(task_type, task_id, 'output.jsonl', output)
                _set_progress(task_type, task_id, len(_rows(task_type, task_id, 'output.jsonl')))

            if retrying:
                retry_path.unlink(missing_ok=True)
            outputs = _rows(task_type, task_id, 'output.jsonl')
            inputs = _rows(task_type, task_id, 'input.jsonl')
            missing_count = max(0, len(inputs) - len(outputs))
            failures = sum(not row.get('result', {}).get('success') for row in outputs) + missing_count
            status = 'partial_failed' if failures else 'completed'
            _update(task_id, status=status)
            return {'task_id': task_id, 'status': status}

        handler = get_chart_insight_logic if task_type == 'chart' else get_compare_insight_logic
        result = handler(task['payload'])
        if not result.get('success'):
            raise RuntimeError(str(result.get('error') or 'LLM did not return a result'))
        _write(task_type, task_id, 'output.jsonl', {'item_id': task_id, 'result': result})
        _set_progress(task_type, task_id, 1)
        _update(task_id, status='completed')
        return {'task_id': task_id, 'status': 'completed'}
    except Exception as exc:
        _write(task_type, task_id, 'error.jsonl', {
            'item_id': task_id, 'error_type': type(exc).__name__, 'error': str(exc),
            'traceback': traceback.format_exc(), 'failed_at': datetime.now(timezone.utc).isoformat(),
        })
        _update(task_id, status='failed')
        return {'task_id': task_id, 'status': 'failed'}


def requeue_annual_report_item(task_id, owner_id, item_id):
    task_id, item_id = str(task_id), str(item_id)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT TaskType,Status FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?', (task_id, str(owner_id)))
        row = cursor.fetchone()
        if not row or row[0] not in {'annual_report', 'comparison_report'} or row[1] not in COMPLETED_STATUSES:
            return False
        task_type = row[0]
        request = next((entry for entry in _rows(task_type, task_id, 'input.jsonl') if entry.get('custom_id') == item_id), None)
        if not request:
            return False
        _rewrite(task_type, task_id, 'retry.jsonl', [request])
        _rewrite(task_type, task_id, 'output.jsonl', [
            entry for entry in _rows(task_type, task_id, 'output.jsonl') if entry.get('custom_id') != item_id
        ])
        _set_progress(task_type, task_id, len(_rows(task_type, task_id, 'output.jsonl')))
        cursor.execute(
            """UPDATE dbo.LLMTaskWorker
               SET Status='queued', WorkerID=NULL, CreatedAt=SYSDATETIMEOFFSET(), CompletedAt=NULL
               WHERE TaskID=? AND OwnerID=?""",
            (task_id, str(owner_id)),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()


def recover_running_llm_tasks():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE dbo.LLMTaskWorker SET Status='queued', WorkerID=NULL WHERE Status='running'")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def run_worker(worker_id=None, poll_seconds=2):
    worker_id = worker_id or f"{os.environ.get('COMPUTERNAME', 'worker')}-{os.getpid()}"
    recover_running_llm_tasks()
    while True:
        process_next_llm_task(worker_id)
        time.sleep(poll_seconds)


def delete_llm_task(task_id, owner_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT TaskType FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?', (str(task_id), str(owner_id)))
        row = cursor.fetchone()
        if not row:
            return False
        cursor.execute('DELETE FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=?', (str(task_id), str(owner_id)))
        conn.commit()
        shutil.rmtree(_dir(row[0], task_id), ignore_errors=True)
        return cursor.rowcount > 0
    finally:
        conn.close()
