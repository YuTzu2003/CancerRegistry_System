from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import json
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "cancer-registry-cleansing-module-secret"

# ---- Config ---------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATA_FOLDER = os.path.join(BASE_DIR, "data")
FORMATS_PATH = os.path.join(DATA_FOLDER, "reference_formats.json")
ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32MB

# ---- Sidebar --------------------------------------------------------------
NAV_ITEMS = [
    {"endpoint": "dashboard",     "title": "首頁總覽",    "icon": "bi-house-door"},
    {"endpoint": "data_cleaning", "title": "資料清洗模組", "icon": "bi-funnel"},
    {"endpoint": "reports",       "title": "申報紀錄",    "icon": "bi-file-earmark-text"},
    {"endpoint": "analytics",     "title": "統計分析",    "icon": "bi-bar-chart"},
    {"endpoint": "settings",      "title": "系統設定",    "icon": "bi-gear"},
]


@app.context_processor
def inject_nav():
    return {"nav_items": NAV_ITEMS}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---- Reference formats (JSON-backed CRUD) ---------------------------------
DEFAULT_FORMATS = [
    {"id": "fmt-42",  "name": "42欄位",  "version": "2011 v7", "updated": "2017/12/04"},
    {"id": "fmt-45",  "name": "45欄位",  "version": "2018 v7", "updated": "2024/12/20"},
    {"id": "fmt-50",  "name": "50欄位",  "version": "2025 v1", "updated": "2025/12/04"},
    {"id": "fmt-114", "name": "114欄位", "version": "2011 v7", "updated": "2017/12/04"},
    {"id": "fmt-115", "name": "115欄位", "version": "2018 v7", "updated": "2024/12/20"},
    {"id": "fmt-129", "name": "129欄位", "version": "2025 v1", "updated": "2025/12/04"},
]


def load_formats():
    if not os.path.exists(FORMATS_PATH):
        with open(FORMATS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_FORMATS, f, ensure_ascii=False, indent=2)
        return list(DEFAULT_FORMATS)
    with open(FORMATS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_formats(items):
    with open(FORMATS_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# ---- Pages ----------------------------------------------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@app.route("/clean")
def data_cleaning():
    formats = load_formats()
    return render_template(
        "clean.html",
        active="data_cleaning",
        formats=formats,
    )


@app.route("/reports")
def reports():
    return render_template("reports.html", active="reports")


@app.route("/analytics")
def analytics():
    return render_template("analytics.html", active="analytics")


@app.route("/settings")
def settings():
    return render_template("settings.html", active="settings")


# ---- API: Reference format CRUD -------------------------------------------
@app.route("/api/formats", methods=["GET"])
def api_formats_list():
    return jsonify(load_formats())


@app.route("/api/formats", methods=["POST"])
def api_formats_create():
    payload = request.get_json(silent=True) or {}
    new_item = {
        "id": f"fmt-{uuid.uuid4().hex[:8]}",
        "name": (payload.get("name") or "").strip() or "未命名格式",
        "version": (payload.get("version") or "").strip() or "v1.0",
        "updated": (payload.get("updated") or "").strip(),
    }
    items = load_formats()
    items.append(new_item)
    save_formats(items)
    return jsonify(new_item), 201


@app.route("/api/formats/<fmt_id>", methods=["PUT"])
def api_formats_update(fmt_id):
    payload = request.get_json(silent=True) or {}
    items = load_formats()
    updated = None
    for it in items:
        if it["id"] == fmt_id:
            it["name"] = (payload.get("name") or it["name"]).strip()
            it["version"] = (payload.get("version") or it["version"]).strip()
            it["updated"] = (payload.get("updated") or it.get("updated", "")).strip()
            updated = it
            break
    if not updated:
        return jsonify({"error": "not found"}), 404
    save_formats(items)
    return jsonify(updated)


@app.route("/api/formats/<fmt_id>", methods=["DELETE"])
def api_formats_delete(fmt_id):
    items = load_formats()
    new_items = [x for x in items if x["id"] != fmt_id]
    if len(new_items) == len(items):
        return jsonify({"error": "not found"}), 404
    save_formats(new_items)
    return jsonify({"ok": True})


# ---- API: Cleaning pipeline (mock, UI-ready placeholders) ------------------
@app.route("/api/clean", methods=["POST"])
def api_clean():
    """
    Accepts: multipart/form-data with
        - data_file  (csv/xls/xlsx)
        - format_id  (reference format id)
    Returns a mocked cleaning result structure so the frontend can render
    both the case detail list and the analysis view. Replace the body of
    this function with real cleaning logic later.
    """
    file = request.files.get("data_file")
    format_id = request.form.get("format_id", "")

    if not file or file.filename == "":
        return jsonify({"ok": False, "error": "請選擇要上傳的檔案"}), 400
    if not allowed_file(file.filename):
        return jsonify({"ok": False, "error": "不支援的檔案格式，僅接受 CSV / Excel"}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)
    size_kb = round(os.path.getsize(save_path) / 1024, 2)

    formats = load_formats()
    fmt = next((f for f in formats if f["id"] == format_id), None)

    # Placeholder cleaning output. Keep the shape stable for the UI layer.
    result = {
        "ok": True,
        "file": {"name": filename, "size_kb": size_kb},
        "format": fmt or {"name": "未指定", "code": "-"},
        "summary": {
            "total_rows": 0,
            "passed_rows": 0,
            "error_rows": 0,
            "warning_rows": 0,
        },
        "issues": [],          # 清洗個案清單明細
        "analysis": {          # 清洗結果分析
            "by_field": [],
            "by_type": [],
        },
        "output_fields": [],   # 可勾選輸出欄位（前端呈現空白佔位）
    }
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
