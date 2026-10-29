"""HTTP seam for the isolated survival report workflow."""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, send_file, session

from modules.services.auth import login_required

from .export_bundle import build_pptx_download
from .job_store import JobNotFound, JobStore
from .parser import UnsupportedSourceFormat, parse_survival_workbook
from .report_builder import (
    DeckOverride,
    DisplayOverride,
    apply_display_overrides,
    build_report_batch,
)


survival_report_bp = Blueprint(
    "survival_report",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/survival-report/static",
)

_ALLOWED_EXTENSIONS = {".xls", ".xlsx"}
_TEMPLATE_PATH = Path(__file__).with_name("assets") / "survival_report_template.pptx"


def _owner_id() -> str:
    return str(session.get("id", ""))


def _job_store() -> JobStore:
    configured = current_app.config.get("SURVIVAL_REPORT_JOB_ROOT")
    ttl = current_app.config.get("SURVIVAL_REPORT_JOB_TTL_SECONDS", 3600)
    return JobStore(Path(configured) if configured else None, ttl_seconds=ttl)


def _safe_original_filename(filename: str) -> str:
    return str(filename or "").replace("\\", "/").split("/")[-1].strip()


def _not_found():
    return jsonify({"ok": False, "error": "找不到作業。"}), 404


@survival_report_bp.get("/survival-report")
@login_required
def index():
    return render_template("survival_report/index.html", active="survival_report.index")


@survival_report_bp.post("/api/survival-report/preview")
@login_required
def preview():
    uploads = request.files.getlist("files")
    if not uploads or not any(item.filename for item in uploads):
        return jsonify({"ok": False, "error": "請至少選擇一個 Excel 檔案。"}), 400
    upload_root_config = current_app.config.get("SURVIVAL_REPORT_UPLOAD_ROOT")
    upload_root = Path(upload_root_config) if upload_root_config else Path(tempfile.gettempdir()) / "cancer_registry_survival_uploads"
    upload_root.mkdir(parents=True, exist_ok=True)
    parsed = []
    results = []
    with tempfile.TemporaryDirectory(prefix="survival-", dir=upload_root) as temporary:
        temporary_root = Path(temporary)
        for upload in uploads:
            original_name = _safe_original_filename(upload.filename)
            extension = Path(original_name).suffix.lower()
            if extension not in _ALLOWED_EXTENSIONS:
                results.append({"filename": original_name, "ok": False, "error": "僅支援 .xls 與 .xlsx。"})
                continue
            temporary_path = temporary_root / f"{uuid.uuid4().hex}{extension}"
            try:
                upload.save(temporary_path)
                workbook = parse_survival_workbook(temporary_path, original_name)
                parsed.append(workbook)
                result = {
                    "filename": original_name,
                    "ok": bool(workbook.stage_series),
                    "format": workbook.source_format.value,
                    "hospital_name": workbook.hospital_name,
                    "period": f"{workbook.period_start}-{workbook.period_end}",
                    "issue_count": len(workbook.issues),
                }
                if not workbook.stage_series:
                    result["error"] = "未找到可用的存活率資料。"
                results.append(result)
            except (UnsupportedSourceFormat, ValueError) as error:
                results.append({"filename": original_name, "ok": False, "error": str(error)})
            except Exception as error:
                logging.error(
                    "Unexpected survival report parser failure for %s (%s)",
                    original_name,
                    type(error).__name__,
                )
                results.append(
                    {
                        "filename": original_name,
                        "ok": False,
                        "error": "檔案無法解析，請確認內容後重新上傳。",
                    }
                )
            finally:
                temporary_path.unlink(missing_ok=True)
    if not parsed:
        return jsonify({"ok": False, "error": "沒有可建立預覽的檔案。", "files": results}), 400
    batch = build_report_batch(parsed)
    if not batch.decks:
        return jsonify({"ok": False, "error": "沒有可建立預覽的報表。", "files": results}), 400
    store = _job_store()
    store.cleanup_expired()
    job_id = store.create(_owner_id(), batch)
    return jsonify({"ok": True, "job_id": job_id, "files": results, "batch": batch.to_dict()})


@survival_report_bp.get("/api/survival-report/jobs/<job_id>")
@login_required
def get_job(job_id: str):
    try:
        stored = _job_store().load(_owner_id(), job_id)
    except JobNotFound:
        return _not_found()
    return jsonify({"ok": True, "job_id": stored.job_id, "batch": stored.batch.to_dict()})


@survival_report_bp.patch("/api/survival-report/jobs/<job_id>")
@login_required
def update_job(job_id: str):
    payload = request.get_json(silent=True) or {}
    tables = payload.get("tables")
    decks = payload.get("decks", [])
    if not isinstance(tables, list):
        return jsonify({"ok": False, "error": "tables 必須是陣列。"}), 400
    if not isinstance(decks, list):
        return jsonify({"ok": False, "error": "decks 必須是陣列。"}), 400
    try:
        store = _job_store()
        stored = store.load(_owner_id(), job_id)
        overrides = [DisplayOverride.from_dict(item) for item in tables if isinstance(item, dict)]
        deck_overrides = [DeckOverride.from_dict(item) for item in decks if isinstance(item, dict)]
        batch = apply_display_overrides(stored.batch, overrides, deck_overrides)
        store.save_batch(_owner_id(), job_id, batch)
    except JobNotFound:
        return _not_found()
    except (KeyError, TypeError, ValueError) as error:
        return jsonify({"ok": False, "error": f"預覽設定無效：{error}"}), 400
    return jsonify({"ok": True, "job_id": job_id, "batch": batch.to_dict()})


@survival_report_bp.delete("/api/survival-report/jobs/<job_id>")
@login_required
def delete_job(job_id: str):
    try:
        _job_store().delete(_owner_id(), job_id)
    except JobNotFound:
        return _not_found()
    return jsonify({"ok": True})


def _load_selected_job(job_id: str):
    stored = _job_store().load(_owner_id(), job_id)
    if not stored.batch.selected_decks:
        raise ValueError("沒有已選取的 PPT。")
    return stored


@survival_report_bp.post("/api/survival-report/jobs/<job_id>/export/pptx")
@login_required
def export_pptx(job_id: str):
    try:
        stored = _load_selected_job(job_id)
        artifact = build_pptx_download(stored.batch.selected_decks, _TEMPLATE_PATH)
    except JobNotFound:
        return _not_found()
    except ValueError as error:
        return jsonify({"ok": False, "error": str(error)}), 400
    return send_file(
        artifact.content,
        mimetype=artifact.mimetype,
        as_attachment=True,
        download_name=artifact.filename,
    )
