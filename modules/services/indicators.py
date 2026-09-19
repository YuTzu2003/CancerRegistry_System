import os
import re
import shutil
import uuid

import pandas as pd
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from modules.services.auth import login_required
from modules.blueprint.indicators.analysis import run_indicators_analysis


indicators_bp = Blueprint(
    "indicators",
    __name__,
    template_folder="../blueprint/indicators/templates",
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INDICATORS_DATA_DIR = os.path.join(BASE_DIR, "tasks", "data", "indicators")
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
YEAR_COLUMN_HINTS = ("didiag", "診斷日期", "診斷年度", "diagnosis date", "diagnosis year")
MAX_SESSION_SOURCES = 10


def _read_uploaded_file(path, extension, nrows=5000):
    # 癌登欄位含大量前導零代碼與特殊日期，必須以文字保留原值。
    options = {"dtype": str}
    if nrows is not None:
        options["nrows"] = nrows
    if extension == ".csv":
        return pd.read_csv(path, **options)
    return pd.read_excel(path, **options)


def _find_diagnosis_year_column(columns):
    normalized = {str(column).strip().lower(): column for column in columns}
    for hint in YEAR_COLUMN_HINTS:
        if hint in normalized:
            return normalized[hint]
    for column in columns:
        column_text = str(column).strip().lower()
        if any(hint in column_text for hint in YEAR_COLUMN_HINTS):
            return column
    return None


def _extract_years(values):
    years = []
    for value in values.dropna():
        match = re.search(r"(?<!\d)((?:19|20)\d{2})", str(value))
        if match:
            years.append(int(match.group(1)))
    return sorted(set(years))


def _stored_sources():
    sources = session.get("indicators_sources") or []
    valid_sources = [
        source for source in sources
        if isinstance(source, dict) and source.get("file_id") and source.get("path") and os.path.isfile(source["path"])
    ]
    if len(valid_sources) != len(sources):
        session["indicators_sources"] = valid_sources
    return valid_sources


def _source_response(source):
    return {
        "file_id": source["file_id"],
        "filename": source["filename"],
        "file_size": source.get("file_size", 0),
        "record_count": source.get("record_count", 0),
        "year_column": source.get("year_column", ""),
        "years": source.get("years", []),
    }


def _delete_source_file(source):
    stored_path = os.path.abspath(source.get("path") or "")
    data_root = os.path.abspath(INDICATORS_DATA_DIR)
    if not stored_path or os.path.commonpath([data_root, stored_path]) != data_root:
        return
    source_folder = os.path.dirname(stored_path)
    if os.path.isdir(source_folder):
        shutil.rmtree(source_folder)


def _clear_indicator_sources():
    """Remove all uploaded indicator files associated with the current session."""
    sources = session.get("indicators_sources") or []
    for source in sources:
        if not isinstance(source, dict):
            continue
        try:
            _delete_source_file(source)
        except OSError as exc:
            current_app.logger.warning(
                "Unable to remove indicator source %s during page refresh: %s",
                source.get("file_id"),
                exc,
            )
    session.pop("indicators_sources", None)
    session.pop("indicators_source", None)


@indicators_bp.route("/indicators")
@login_required
def indicators():
    return render_template("indicators.html", active="indicators")


@indicators_bp.route("/monitoring")
@login_required
def monitoring_legacy():
    return redirect(url_for("indicators.indicators"))


@indicators_bp.route("/api/monitoring/upload", methods=["POST"])
@indicators_bp.route("/api/indicators/upload", methods=["POST"])
@login_required
def upload_indicators_source():
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"ok": False, "error": "請選擇要分析的資料檔。"}), 400

    original_name = uploaded_file.filename
    extension = os.path.splitext(original_name)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        return jsonify({"ok": False, "error": "請上傳 Excel 或 CSV 檔案。"}), 400

    sources = _stored_sources()
    if len(sources) >= MAX_SESSION_SOURCES:
        return jsonify({"ok": False, "error": f"檔案清單最多保留 {MAX_SESSION_SOURCES} 個檔案，請先刪除不需要的檔案。"}), 400

    safe_name = secure_filename(original_name) or f"indicators_source{extension}"
    file_id = str(uuid.uuid4())
    folder = os.path.join(INDICATORS_DATA_DIR, file_id)
    stored_path = os.path.join(folder, safe_name)

    try:
        os.makedirs(folder, exist_ok=True)
        uploaded_file.save(stored_path)
        dataframe = _read_uploaded_file(stored_path, extension, nrows=None)
        year_column = _find_diagnosis_year_column(dataframe.columns)
        years = _extract_years(dataframe[year_column]) if year_column is not None else []
    except Exception as exc:
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"ok": False, "error": f"無法讀取資料檔：{exc}"}), 400

    if not years:
        shutil.rmtree(folder, ignore_errors=True)
        return jsonify({"ok": False, "error": "找不到可用的診斷年度欄位，請確認資料欄位內容。"}), 400

    source = {
        "file_id": file_id,
        "filename": original_name,
        "path": stored_path,
        "file_size": os.path.getsize(stored_path),
        "record_count": int(len(dataframe)),
        "year_column": str(year_column) if year_column is not None else "",
        "years": years,
    }
    sources.append(source)
    session["indicators_sources"] = sources
    session["indicators_source"] = source
    return jsonify({"ok": True, **_source_response(source)})


@indicators_bp.route("/api/indicators/sources", methods=["GET"])
@login_required
def list_indicators_sources():
    active_source = session.get("indicators_source") or {}
    return jsonify({
        "ok": True,
        "active_file_id": active_source.get("file_id"),
        "sources": [_source_response(source) for source in _stored_sources()],
    })


@indicators_bp.route("/api/indicators/source/<file_id>/activate", methods=["POST"])
@login_required
def activate_indicators_source(file_id):
    source = next((item for item in _stored_sources() if item["file_id"] == file_id), None)
    if source is None:
        return jsonify({"ok": False, "error": "找不到指定的檔案，請重新上傳。"}), 404
    session["indicators_source"] = source
    return jsonify({"ok": True, **_source_response(source)})


@indicators_bp.route("/api/indicators/source/<file_id>", methods=["DELETE"])
@login_required
def delete_indicators_source(file_id):
    sources = _stored_sources()
    source = next((item for item in sources if item["file_id"] == file_id), None)
    if source is None:
        return jsonify({"ok": False, "error": "找不到指定的檔案。"}), 404

    try:
        _delete_source_file(source)
    except OSError as exc:
        return jsonify({"ok": False, "error": f"無法刪除檔案：{exc}"}), 500

    session["indicators_sources"] = [item for item in sources if item["file_id"] != file_id]
    active_source = session.get("indicators_source") or {}
    if active_source.get("file_id") == file_id:
        session.pop("indicators_source", None)
    return jsonify({"ok": True})


@indicators_bp.route("/api/monitoring/preview", methods=["POST"])
@indicators_bp.route("/api/indicators/preview", methods=["POST"])
@login_required
def preview_indicators():
    source = session.get("indicators_source") or {}
    stored_path = source.get("path")
    if not stored_path or not os.path.isfile(stored_path):
        return jsonify({"ok": False, "error": "請先上傳要分析的資料檔。"}), 400

    payload = request.get_json(silent=True) or {}
    cancers = payload.get("cancers") or []
    year_start = payload.get("year_start")
    year_end = payload.get("year_end")
    try:
        year_start, year_end = int(year_start), int(year_end)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "請選擇起始與結束診斷年度。"}), 400
    if year_start > year_end or not cancers:
        return jsonify({"ok": False, "error": "請確認診斷年度區間與癌別選擇。"}), 400

    extension = os.path.splitext(stored_path)[1].lower()
    try:
        dataframe = _read_uploaded_file(stored_path, extension, nrows=None)
        result = run_indicators_analysis(dataframe, cancers, year_start, year_end)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"產生指標內容失敗：{exc}"}), 500
    return jsonify(result), (200 if result.get("ok") else 400)
