"""Background render queue for dashboard annual-report exports (匯出背景化).

Reuses the dbo.LLMTaskWorker table with TaskType='export_render', but claims and
recovers only its own type, so a dedicated export worker never contends with the
LLM workers (and vice versa). The charts payload and the rendered output live on
disk under tasks/dashboard/export_render/<task_id>/; the SQL row stays small.

DB prerequisite (hospital DB, one-off): the CK_LLMTaskWorker_TaskType check
constraint must allow 'export_render' — see
deploy/database/migrations/2026-11-27_add_export_render_task_type.sql.

End-to-end validation (worker deploy, DB, browser download) requires the
hospital environment; the queue/isolation/ownership logic is unit-tested with a
mocked connection in test/regression/test_export_tasks.py.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXPORT_TASK_TYPE = "export_render"
EXPORT_TASK_ROOT = Path(__file__).resolve().parents[3] / "tasks" / "dashboard" / "export_render"
EXPORT_TASK_TTL_SECONDS = 24 * 3600  # keep finished exports for one day


def _export_browser_max_renders():
    """How many renders a persistent browser serves before it is recycled.

    Keeping one Chromium + Playwright driver alive across exports saves the ~2.5s
    driver startup per export, but a long-lived browser slowly grows memory, so it
    is torn down and relaunched after this many renders. Overridable by env.
    """
    raw = os.environ.get("EXPORT_BROWSER_MAX_RENDERS")
    if raw and raw.strip():
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return 50

_OUTPUT_EXT = {
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def get_conn():
    """Load the DB connection lazily (after Dashboard modules finish importing)."""
    from modules.services.db import get_conn as database_get_conn
    return database_get_conn()


def _task_dir(task_id):
    return EXPORT_TASK_ROOT / str(task_id)


def _payload_path(task_id):
    return _task_dir(task_id) / "payload.json"


def _meta_path(task_id):
    return _task_dir(task_id) / "meta.json"


def _atomic_write_bytes(path: Path, data: bytes):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)  # atomic on the same filesystem


def _atomic_write_json(path: Path, value):
    _atomic_write_bytes(path, json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


# ── enqueue ────────────────────────────────────────────────────────────────
def create_export_task(owner_id, payload):
    """Persist the payload to disk, then enqueue a row. Returns {task_id, status}."""
    task_id = str(uuid.uuid4())
    task_dir = _task_dir(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)
    try:
        _atomic_write_json(_payload_path(task_id), payload)  # payload on disk BEFORE insert
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO dbo.LLMTaskWorker (TaskID, OwnerID, TaskType, Status, ProgressTotal, CreatedAt) "
                "VALUES (?, ?, ?, 'queued', 1, SYSDATETIMEOFFSET())",
                (task_id, str(owner_id), EXPORT_TASK_TYPE),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        # Any failure (payload write, connection, insert) → drop the orphan dir.
        shutil.rmtree(task_dir, ignore_errors=True)
        raise
    return {"task_id": task_id, "status": "queued"}


# ── claim / status update (type-isolated) ───────────────────────────────────
def claim_next_export_task(worker_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            ";WITH candidate AS ("
            "    SELECT TOP (1) * FROM dbo.LLMTaskWorker WITH (UPDLOCK, READPAST, ROWLOCK)"
            "    WHERE Status='queued' AND TaskType=?"
            "    ORDER BY CreatedAt"
            ") UPDATE candidate SET Status='running', WorkerID=?"
            "  OUTPUT inserted.TaskID;",
            (EXPORT_TASK_TYPE, worker_id),
        )
        row = cursor.fetchone()
        conn.commit()
        if not row:
            return None
        task_id = str(row[0])
        logging.info("Export worker %s claimed task %s", worker_id, task_id)
        return task_id
    finally:
        conn.close()


def _update_status(task_id, status):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dbo.LLMTaskWorker "
            "SET Status=?, CompletedAt=CASE WHEN ? IN ('completed','failed') THEN SYSDATETIMEOFFSET() ELSE CompletedAt END "
            "WHERE TaskID=? AND TaskType=?",
            (status, status, str(task_id), EXPORT_TASK_TYPE),
        )
        conn.commit()
    finally:
        conn.close()


def recover_running_export_tasks(worker_id):
    """Requeue only this worker's own abandoned export tasks (type-filtered so a
    worker_id collision with an LLM worker can never requeue an LLM task)."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dbo.LLMTaskWorker SET Status='queued', WorkerID=NULL "
            "WHERE Status='running' AND WorkerID=? AND TaskType=?",
            (worker_id, EXPORT_TASK_TYPE),
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# ── persistent browser (reused across renders, recycled by render count) ─────
def _default_browser_launcher():
    """Start Playwright + Chromium. Imported lazily so loading this module (e.g.
    the file-path import in tests) never pulls Playwright. If launch() fails after
    the driver started, stop the driver before re-raising so it is not leaked."""
    from playwright.sync_api import sync_playwright
    playwright = sync_playwright().start()
    try:
        browser = playwright.chromium.launch(headless=True)
    except Exception:
        try:
            playwright.stop()
        except Exception:
            logging.exception("Error stopping Playwright after a failed browser launch")
        raise
    return playwright, browser


class _PersistentBrowser:
    """One long-lived Chromium the worker reuses across exports, recycled after
    ``max_renders`` renders and rebuilt automatically if it crashes/disconnects.

    Single-threaded by contract: the worker loop is the only caller, so the
    thread-affine Playwright sync API is always driven from the same thread.
    """

    def __init__(self, max_renders=None, launcher=_default_browser_launcher):
        self._max = max_renders if max_renders is not None else _export_browser_max_renders()
        self._launch = launcher
        self._playwright = None
        self._browser = None
        self._renders = 0

    def _teardown(self):
        # Clear state FIRST so a throwing close()/stop() can never leave a stale
        # (and possibly wedged) handle behind; then close each, fully guarded —
        # even the attribute access — so teardown itself never raises.
        browser, playwright = self._browser, self._playwright
        self._browser = None
        self._playwright = None
        self._renders = 0
        for obj, method in ((browser, "close"), (playwright, "stop")):
            if obj is None:
                continue
            try:
                closer = getattr(obj, method, None)
                if closer is not None:
                    closer()
            except Exception:
                logging.exception("Error while tearing down the export browser")

    def _alive(self):
        if self._browser is None:
            return False
        is_connected = getattr(self._browser, "is_connected", None)
        try:
            return bool(is_connected()) if is_connected else True
        except Exception:
            return False

    def get(self):
        """Return a live browser, (re)launching if absent, recycled, or dead."""
        if self._alive() and self._renders < self._max:
            return self._browser
        if self._browser is not None:
            logging.info("Recycling export browser (renders=%s, max=%s, alive=%s)",
                         self._renders, self._max, self._alive())
            self._teardown()
        self._playwright, self._browser = self._launch()
        self._renders = 0
        logging.info("Export browser launched (recycle after %s renders)", self._max)
        return self._browser

    def mark_rendered(self):
        self._renders += 1

    def on_error(self):
        """A render raised; the browser may be wedged, so drop it and relaunch next time."""
        self._teardown()

    def close(self):
        self._teardown()


# ── process one task ────────────────────────────────────────────────────────
def _render(payload, output_dir, get_browser=None):
    """Render the export. Isolated behind one call so the worker path is testable
    without importing the heavy export_report module (and its Playwright deps).
    ``get_browser`` (when given) is a zero-arg callable the renderer invokes only
    if it actually needs a browser (so a Word-only export never launches one)."""
    from modules.blueprint.dashboard.export_report import generate_export_files
    return generate_export_files(
        payload.get("format_pdf", True),
        payload.get("format_word", False),
        payload.get("charts") or [],
        output_dir,
        payload.get("export_language", "zh-TW"),
        get_browser=get_browser,
    )


def process_next_export_task(worker_id, browser_pool=None):
    task_id = claim_next_export_task(worker_id)
    if not task_id:
        return None
    # The renderer pulls the browser lazily; we only count / recycle it when it
    # was actually used, so a Word-only export (which never launches Chromium) is
    # neither charged a render slot nor failed by a browser problem.
    used = {"browser": False}

    def _acquire_browser():
        used["browser"] = True
        return browser_pool.get()

    try:
        payload = _read_json(_payload_path(task_id))
        if not (payload.get("charts") or []):
            raise ValueError("沒有圖表資料可匯出")
        provider = _acquire_browser if browser_pool is not None else None
        file_obj, mimetype, download_name = _render(payload, str(_task_dir(task_id)), get_browser=provider)
        if browser_pool is not None and used["browser"]:
            browser_pool.mark_rendered()
        if not file_obj:
            raise RuntimeError("無法產生匯出檔案")
        output_file = f"output{_OUTPUT_EXT.get(mimetype, '.bin')}"
        # Write the output, then the meta, then flip status — a reader never sees
        # 'completed' before the bytes are on disk (restart re-run overwrites).
        _atomic_write_bytes(_task_dir(task_id) / output_file, file_obj.getvalue())
        _atomic_write_json(_meta_path(task_id), {
            "OutputFile": output_file, "OutputName": download_name, "Mimetype": mimetype,
        })
        _update_status(task_id, "completed")
        return {"task_id": task_id, "status": "completed"}
    except Exception as exc:
        logging.exception("Export task %s failed", task_id)
        # A render that obtained the browser may have left it wedged; drop it so the
        # next task relaunches a clean one. Guard it so recycling can never prevent
        # the failed-status update below (which must always run).
        if browser_pool is not None and used["browser"]:
            try:
                browser_pool.on_error()
            except Exception:
                logging.exception("Error recycling export browser after a failed task")
        # The error handler must never raise, or the worker loop would die and
        # leave the task 'running' (it is instead recovered on the next restart).
        try:
            _atomic_write_json(_meta_path(task_id), {
                "Error": str(exc), "ErrorType": type(exc).__name__,
                "Traceback": traceback.format_exc(),
                "failed_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            logging.exception("Could not write error meta for export task %s", task_id)
        try:
            _update_status(task_id, "failed")
        except Exception:
            logging.exception("Could not mark export task %s failed", task_id)
        return {"task_id": task_id, "status": "failed"}


# ── status / output read (ownership + type enforced) ────────────────────────
def get_export_task(task_id, owner_id):
    """Status for the owner's export task, or None if not theirs/not an export."""
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Status FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=? AND TaskType=?",
            (str(task_id), str(owner_id), EXPORT_TASK_TYPE),
        )
        row = cursor.fetchone()
        if not row:
            return None
        status = row[0]
        meta = _read_json(_meta_path(task_id))
        result = {"task_id": str(task_id), "status": status}
        if status == "failed":
            result["error"] = meta.get("Error") or "匯出失敗"
        if status == "completed":
            result["output_name"] = meta.get("OutputName")
        return result
    finally:
        conn.close()


def read_export_output(task_id, owner_id):
    """Return (path, mimetype, download_name) for a completed, owned export.

    Returns None unless the SQL row is this owner's completed export task AND the
    output file is actually present on disk.
    """
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Status FROM dbo.LLMTaskWorker WHERE TaskID=? AND OwnerID=? AND TaskType=?",
            (str(task_id), str(owner_id), EXPORT_TASK_TYPE),
        )
        row = cursor.fetchone()
    finally:
        conn.close()
    if not row or row[0] != "completed":
        return None
    meta = _read_json(_meta_path(task_id))
    output_file = meta.get("OutputFile")
    if not output_file:
        return None
    # Guard against a tampered meta escaping the task directory.
    path = (_task_dir(task_id) / output_file).resolve()
    if path.parent != _task_dir(task_id).resolve() or not path.is_file():
        return None
    return path, meta.get("Mimetype") or "application/octet-stream", meta.get("OutputName") or output_file


# ── worker loop ─────────────────────────────────────────────────────────────
def _default_worker_id():
    # Stable across restarts (no PID): a restarted worker must keep the same id so
    # recover_running_export_tasks() requeues its own abandoned 'running' tasks.
    number = os.environ.get("EXPORT_WORKER_NUMBER")
    if number and number.strip():
        return f"export-{int(number):02d}"
    return f"export-{os.environ.get('COMPUTERNAME', 'worker')}"


def run_export_worker(worker_id=None, poll_seconds=2):
    worker_id = worker_id or _default_worker_id()
    try:
        recovered = recover_running_export_tasks(worker_id)
        logging.info("Export worker %s is ready; recovered %s running task(s)", worker_id, recovered)
    except Exception:
        # A DB outage at startup must not kill the worker; the loop below retries
        # and the abandoned 'running' tasks are recovered on the next restart.
        logging.exception("Export worker %s could not recover running tasks at startup", worker_id)
    # One persistent browser reused across exports; lazily launched on first render
    # and recycled by render count (or on crash) inside the pool.
    browser_pool = _PersistentBrowser()
    try:
        while True:
            try:
                result = process_next_export_task(worker_id, browser_pool=browser_pool)
                if result:
                    logging.info("Export task %s finished with status %s", result["task_id"], result["status"])
            except Exception:
                # Keep the worker alive through transient DB/render failures.
                logging.exception("Export worker loop iteration failed")
            time.sleep(poll_seconds)
    finally:
        browser_pool.close()


# ── retention sweep (terminal tasks only) ───────────────────────────────────
def cleanup_expired_export_tasks(now=None):
    """Delete finished export tasks (row + files) older than the TTL.

    Only terminal rows (completed/failed) are removed; queued/running payloads are
    never touched. Returns the number of tasks removed.
    """
    # Compute the cutoff ONCE and pass it to both statements, so SELECT and DELETE
    # match exactly the same rows (no re-evaluated-clock window between them).
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    cutoff = current - timedelta(seconds=EXPORT_TASK_TTL_SECONDS)
    terminal_filter = "TaskType=? AND Status IN ('completed','failed') AND CompletedAt < ?"
    params = (EXPORT_TASK_TYPE, cutoff)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT TaskID FROM dbo.LLMTaskWorker WHERE {terminal_filter}", params)
        task_ids = [str(row[0]) for row in cursor.fetchall()]
        if not task_ids:
            return 0
        # DELETE by the same predicate (not an id list): self-guarded against a
        # state change between the two statements, and never hits SQL Server's
        # 2100-parameter limit no matter how many rows expired.
        cursor.execute(f"DELETE FROM dbo.LLMTaskWorker WHERE {terminal_filter}", params)
        conn.commit()
    finally:
        conn.close()
    root = EXPORT_TASK_ROOT.resolve()
    for task_id in task_ids:
        path = _task_dir(task_id).resolve()
        if path.parent == root and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    return len(task_ids)
