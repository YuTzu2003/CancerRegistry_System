import os
import re
import uuid

import pandas as pd
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
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


def _read_uploaded_file(path, extension, nrows=5000):
    options = {"nrows": nrows} if nrows is not None else {}
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

    safe_name = secure_filename(original_name) or f"indicators_source{extension}"
    file_id = str(uuid.uuid4())
    folder = os.path.join(INDICATORS_DATA_DIR, file_id)
    os.makedirs(folder, exist_ok=True)
    stored_path = os.path.join(folder, safe_name)

    try:
        uploaded_file.save(stored_path)
        dataframe = _read_uploaded_file(stored_path, extension)
        year_column = _find_diagnosis_year_column(dataframe.columns)
        years = _extract_years(dataframe[year_column]) if year_column is not None else []
    except Exception as exc:
        if os.path.exists(stored_path):
            os.remove(stored_path)
        return jsonify({"ok": False, "error": f"無法讀取資料檔：{exc}"}), 400

    session["indicators_source"] = {
        "file_id": file_id,
        "filename": original_name,
        "path": stored_path,
    }
    return jsonify({
        "ok": True,
        "filename": original_name,
        "record_count": int(len(dataframe)),
        "year_column": str(year_column) if year_column is not None else "",
        "years": years,
    })
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