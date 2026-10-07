import os
import re
import shutil
import uuid
import math
import hashlib
import json
import pandas as pd
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.utils import secure_filename
from modules.services.auth import login_required, position_required
from modules.services.audit import write_audit_log
from modules.services.db import get_conn
from modules.blueprint.dashboard.input_format import read_csv_with_encoding, validate_and_normalize_dashboard_upload
from modules.blueprint.dashboard.llm_tasks import create_llm_task, find_reusable_llm_task, get_llm_task_payload
from modules.blueprint.indicators.analysis import build_indicators_export_frame, run_indicators_analysis
from modules.blueprint.indicators.catalog import get_cancer_label, get_indicator_rules
from modules.blueprint.indicators.excel_export import create_indicators_excel
from modules.blueprint.indicators.export_report import generate_indicator_export_files
from modules.blueprint.indicators.text_input import convert_indicator_txt_to_excel

indicators_bp = Blueprint("indicators",__name__,template_folder="../blueprint/indicators/templates",)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INDICATORS_DATA_DIR = os.path.join(BASE_DIR, "tasks", "data", "indicators")
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".txt"}
DIAGNOSIS_DATE_CODE = "2.5"
CANONICAL_HEADER_PATTERN = re.compile(r"^\d+(?:\.\d+)*(?:$|[^0-9.])")
MAX_SESSION_SOURCES = 10
INDICATOR_NARRATIVE_PROMPT_VERSION = "2026-09-30-concise-status-summary-v10"
INDICATOR_THRESHOLD_EDITOR_POSITIONS = frozenset({"Admin", "Doctor", "Ctr"})

def _read_uploaded_file(path, extension, nrows=5000):
    options = {"dtype": str}
    if nrows is not None:
        options["nrows"] = nrows
    if extension == ".csv":
        return read_csv_with_encoding(path, **options)
    return pd.read_excel(path, **options)

def _find_diagnosis_year_column(columns):
    for column in columns:
        if str(column).strip().startswith(DIAGNOSIS_DATE_CODE):
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
    valid_sources = []
    changed = False
    for source in sources:
        if not isinstance(source, dict) or not source.get("file_id") or not source.get("path"):
            continue
        if not os.path.isfile(source["path"]):
            continue
        if source.get("header_normalized"):
            valid_sources.append(source)
            continue
        try:
            _normalize_indicator_source(source)
            changed = True
        except Exception as exc:
            current_app.logger.warning("Unable to normalize indicator source %s: %s", source.get("file_id"), exc)
        valid_sources.append(source)
    if changed or len(valid_sources) != len(sources):
        session["indicators_sources"] = valid_sources
    return valid_sources

def _normalize_indicator_source(source):
    path = source["path"]
    extension = os.path.splitext(path)[1].lower().lstrip(".")
    headers = _read_uploaded_file(path, f".{extension}", nrows=0).columns
    if source.get("header_normalized") and any(
        CANONICAL_HEADER_PATTERN.match(str(header).strip()) for header in headers
    ):
        return source
    normalized_path = validate_and_normalize_dashboard_upload(
        path,
        extension,
        "original",
        connection_factory=get_conn,
    )
    source["path"] = normalized_path
    source["header_normalized"] = True
    source["file_size"] = os.path.getsize(normalized_path)
    return source

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

@indicators_bp.route("/indicators")
@login_required
def indicators():
    return render_template(
        "indicators.html",
        active="indicators",
        can_manage_thresholds=session.get("position") in INDICATOR_THRESHOLD_EDITOR_POSITIONS,
    )

@indicators_bp.route("/monitoring")
@login_required
def monitoring_legacy():
    return redirect(url_for("indicators.indicators"))


@indicators_bp.route("/indicators/export-report")
@login_required
def indicators_export_report_page():
    return render_template("indicators_export_report.html", active="indicators")


@indicators_bp.route("/api/indicators/export", methods=["POST"])
@login_required
def export_indicators_report():
    payload = request.get_json(silent=True) or {}
    format_pdf = bool(payload.get("format_pdf", True))
    format_word = bool(payload.get("format_word", False))
    charts = payload.get("charts") or []
    if not isinstance(charts, list) or not charts:
        return jsonify({"ok": False, "error": "沒有監測指標資料可匯出。"}), 400
    if any(
        chart.get("includeAi", True) and not str(chart.get("llmText") or "").strip()
        for chart in charts
        if isinstance(chart, dict)
    ):
        return jsonify({"ok": False, "error": "請先產生語言模型敘述，再進行預覽或下載!!"}), 400
    if not format_pdf and not format_word:
        return jsonify({"ok": False, "error": "請至少選擇一種匯出格式。"}), 400

    output_dir = os.path.join(INDICATORS_DATA_DIR, "exports")
    try:
        file_obj, mimetype, download_name = generate_indicator_export_files(
            format_pdf,
            format_word,
            charts,
            output_dir,
        )
        if not file_obj:
            return jsonify({"ok": False, "error": "無法產生監測指標匯出檔案。"}), 500
        return send_file(
            file_obj,
            mimetype=mimetype,
            as_attachment=True,
            download_name=download_name,
        )
    except Exception as exc:
        current_app.logger.exception("Monitoring-indicator export failed")
        return jsonify({"ok": False, "error": str(exc)}), 500


@indicators_bp.route("/api/indicators/export-excel", methods=["POST"])
@login_required
def export_indicators_excel():
    source = session.get("indicators_source") or {}
    if source:
        _normalize_indicator_source(source)
        session["indicators_source"] = source
    stored_path = source.get("path")
    if not stored_path or not os.path.isfile(stored_path):
        return jsonify({"ok": False, "error": "請先上傳要匯出的資料檔。"}), 400

    payload = request.get_json(silent=True) or {}
    cancers = payload.get("cancers") or []
    try:
        year_start = int(payload.get("year_start"))
        year_end = int(payload.get("year_end"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "請選擇起始與結束診斷年度。"}), 400
    if year_start > year_end or not cancers:
        return jsonify({"ok": False, "error": "請確認診斷年度區間與癌別選擇。"}), 400

    extension = os.path.splitext(stored_path)[1].lower()
    try:
        dataframe = _read_uploaded_file(stored_path, extension, nrows=None)
        export_frame = build_indicators_export_frame(
            dataframe,
            cancers,
            year_start,
            year_end,
            cancer_label_getter=get_cancer_label,
        )
        file_obj = create_indicators_excel(export_frame, len(dataframe.columns))
        return send_file(
            file_obj,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="indicators_data.xlsx",
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        current_app.logger.exception("Monitoring-indicator Excel export failed")
        return jsonify({"ok": False, "error": f"產生 Excel 失敗：{exc}"}), 500

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
        return jsonify({"ok": False, "error": "請上傳 Excel、CSV 或 TXT 檔案。"}), 400

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
        if extension == ".txt":
            converted_path = os.path.join(folder, f"{os.path.splitext(safe_name)[0]}.xlsx")
            stored_path = convert_indicator_txt_to_excel(
                stored_path,
                converted_path,
                connection_factory=get_conn,
            )
            if not stored_path or not os.path.isfile(stored_path):
                raise ValueError(
                    "無法辨識 TXT 格式；固定欄寬資料僅支援格式 42、45、114、115、129，"
                    "其他 TXT 請提供表頭並使用 Tab、逗號、分號或直線分隔欄位。"
                )
            extension = ".xlsx"
        stored_path = validate_and_normalize_dashboard_upload(
            stored_path,
            extension.lstrip("."),
            "original",
            connection_factory=get_conn,
        )
        extension = os.path.splitext(stored_path)[1].lower()
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
        "header_normalized": True,
    }
    sources.append(source)
    session["indicators_sources"] = sources
    session["indicators_source"] = source
    return jsonify({"ok": True, **_source_response(source)})

@indicators_bp.route("/api/indicators/sources", methods=["GET"])
@login_required
def list_indicators_sources():
    active_source = session.get("indicators_source") or {}
    return jsonify({"ok": True,"active_file_id": active_source.get("file_id"),"sources": [_source_response(source) for source in _stored_sources()],})

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


@indicators_bp.route("/api/indicators/thresholds", methods=["POST"])
@position_required(
    *INDICATOR_THRESHOLD_EDITOR_POSITIONS,
    error_message="權限不足，只有管理員、醫師或癌登師可以修改閾值。",
)
def save_indicator_threshold():
    payload = request.get_json(silent=True) or {}
    cancer_key = str(payload.get("cancer_key") or "").strip()
    try:
        indicator_no = int(payload.get("indicator_no"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "指標編號格式不正確。"}), 400

    rule = get_indicator_rules(cancer_key).get(indicator_no)
    if rule is None:
        return jsonify({"ok": False, "error": "找不到指定的癌別或監測指標。"}), 404

    default_operator = "<=" if rule["type"] == "negative" else ">="
    target_raw = payload.get("target_value")
    if target_raw is None or str(target_raw).strip() == "":
        target_value = None
        target_operator = None
    else:
        try:
            target_value = round(float(target_raw), 2)
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "閾值必須是數字。"}), 400
        if not math.isfinite(target_value) or not 0 <= target_value <= 100:
            return jsonify({"ok": False, "error": "閾值必須介於 0 至 100。"}), 400
        target_operator = str(payload.get("target_operator") or default_operator).strip()
        if target_operator not in {">=", ">", "<=", "<", "="}:
            return jsonify({"ok": False, "error": "閾值比較方式不正確。"}), 400

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dbo.Indicator_definition_metadata SET target_value = ?, target_operator = ? "
            "WHERE cancer_group_key = ? AND indicator_no = ?",
            (target_value, target_operator, cancer_key, indicator_no),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO dbo.Indicator_definition_metadata "
                "(cancer_group_key, indicator_no, target_value, target_operator) VALUES (?, ?, ?, ?)",
                (cancer_key, indicator_no, target_value, target_operator),
            )
        conn.commit()
    finally:
        conn.close()

    write_audit_log(
        "indicators_threshold_update",
        {
            "cancer_key": cancer_key,
            "indicator_no": indicator_no,
            "target_value": target_value,
            "target_operator": target_operator,
        },
    )
    return jsonify({
        "ok": True,
        "cancer_key": cancer_key,
        "indicator_no": indicator_no,
        "target_value": target_value,
        "target_operator": target_operator or default_operator,
    })


@indicators_bp.route("/api/indicators/narrative-job", methods=["POST"])
@login_required
def create_indicators_narrative_job():
    payload = request.get_json(silent=True) or {}
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        return jsonify({"ok": False, "error": "沒有可產生敘述的監測指標。"}), 400
    if len(items) > 20:
        return jsonify({"ok": False, "error": "一次最多產生 20 個癌別的監測指標敘述。"}), 400

    mode_ai = str(payload.get("mode_ai") or "balanced").strip()
    if mode_ai not in {"balanced", "formal", "concise"}:
        return jsonify({"ok": False, "error": "敘述風格不正確。"}), 400

    normalized_items = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
            return jsonify({"ok": False, "error": "監測指標敘述資料格式不正確。"}), 400
        indicators = item["data"].get("indicators")
        if not isinstance(indicators, list) or not indicators:
            return jsonify({"ok": False, "error": "沒有可產生敘述的監測指標。"}), 400
        if any(
            not isinstance(indicator, dict)
            or not str(indicator.get("threshold") or "").strip()
            or str(indicator.get("threshold") or "").strip() == "尚未設定"
            for indicator in indicators
        ):
            return jsonify({"ok": False, "error": "請先完成所有監測指標的閾值設定。"}), 400
        normalized_items.append({
            "item_id": str(item.get("item_id") or f"indicators-{index}"),
            "insight_module": "indicators",
            "field_key": str(item.get("field_key") or "監測指標分析"),
            "data": item["data"],
            "fields": [],
            "mode_ai": mode_ai,
            "year_start": str(payload.get("year_start") or ""),
            "year_end": str(payload.get("year_end") or ""),
            "language": "zh-TW",
        })

    task_payload = {
        "items": normalized_items,
        "insight_module": "indicators",
        "prompt_version": INDICATOR_NARRATIVE_PROMPT_VERSION,
        "mode_ai": mode_ai,
        "year_start": str(payload.get("year_start") or ""),
        "year_end": str(payload.get("year_end") or ""),
        "_document_label": "監測指標分析",
        "job_title": "監測指標分析",
    }
    request_signature = {
        "insight_module": "indicators",
        "prompt_version": INDICATOR_NARRATIVE_PROMPT_VERSION,
        "mode_ai": mode_ai,
        "year_start": task_payload["year_start"],
        "year_end": task_payload["year_end"],
        "items": [
            {"field_key": item["field_key"], "data": item["data"]}
            for item in normalized_items
        ],
    }
    request_key = hashlib.sha256(
        json.dumps(request_signature, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    task_payload["_request_key"] = request_key

    if not bool(payload.get("force")):
        existing = find_reusable_llm_task(session.get("id"), "indicator_report", request_key)
        if not existing:
            # Reuse monitoring tasks created before they received a dedicated task type.
            existing = find_reusable_llm_task(session.get("id"), "annual_report", request_key)
        if existing:
            existing_payload = get_llm_task_payload(existing["TaskID"], session.get("id")) or {}
            return jsonify({
                "ok": True,
                "reused": True,
                "task_id": existing["TaskID"],
                "status": existing["Status"],
                "progress_current": existing["ProgressCurrent"],
                "progress_total": existing["ProgressTotal"],
                "item_ids": [item.get("item_id") for item in existing_payload.get("items", [])],
            }), 200

    created = create_llm_task(session.get("id"), "indicator_report", task_payload)
    return jsonify({
        "ok": True,
        "reused": False,
        "item_ids": [item["item_id"] for item in normalized_items],
        **created,
    }), 202

@indicators_bp.route("/api/monitoring/preview", methods=["POST"])
@indicators_bp.route("/api/indicators/preview", methods=["POST"])
@login_required
def preview_indicators():
    source = session.get("indicators_source") or {}
    if source:
        _normalize_indicator_source(source)
        session["indicators_source"] = source
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
