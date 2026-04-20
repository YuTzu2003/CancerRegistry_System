from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import json
import uuid
from werkzeug.utils import secure_filename
from modules.db import get_conn 

app = Flask(__name__)
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


@app.context_processor
def inject_nav():
    NAV_ITEMS = [
        {"endpoint": "dashboard",     "title": "首頁總覽",    "icon": "bi-house-door"},
        {"endpoint": "data_cleaning", "title": "資料清洗模組", "icon": "bi-funnel"},
        {"endpoint": "reports",       "title": "申報紀錄",    "icon": "bi-file-earmark-text"},
        {"endpoint": "analytics",     "title": "統計分析",    "icon": "bi-bar-chart"},
        {"endpoint": "settings",      "title": "系統設定",    "icon": "bi-gear"},
    ]
    return {"nav_items": NAV_ITEMS}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---- Reference formats (JSON-backed CRUD) ---------------------------------
def formats_info():
    formats = []
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [FmtID], [FmtName], [Version], [Revision_date] FROM [DataFormat] ORDER BY FmtName ASC")
    rows = cursor.fetchall()
    for row in rows:
        formats.append({
            "id": str(row.FmtID),
            "name": str(row.FmtName),
            "version": str(row.Version),
            "updated": str(row.Revision_date)
        })
    return formats


# ---- Pages ----------------------------------------------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@app.route("/clean")
def data_cleaning():
    formats = formats_info()
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
# ---- API: Reference format CRUD -------------------------------------------

@app.route("/api/formats", defaults={"fmt_id": None}, methods=["POST"])
@app.route("/api/formats/<fmt_id>", methods=["PUT", "DELETE"])
def manage_format(fmt_id):
    conn = get_conn()
    cursor = conn.cursor()
    if request.method == "POST":
        data = request.json
        name = data.get("name", "").strip()
        version = data.get("version", "").strip()
        updated = data.get("updated", "").strip()
        cursor.execute("""INSERT INTO [DataFormat] ([FmtName], [Version], [Revision_date]) VALUES (?, ?, ?)""", (name, version, updated))
        conn.commit()
        return jsonify({"ok": True, "message": "新增成功"})

    elif request.method == "PUT":
        data = request.json
        name = data.get("name", "").strip()
        version = data.get("version", "").strip()
        updated = data.get("updated", "").strip()
        cursor.execute("""UPDATE [DataFormat] SET [FmtName] = ?, [Version] = ?, [Revision_date] = ? WHERE [FmtID] = ?""", (name, version, updated, fmt_id))
        conn.commit()
        return jsonify({"ok": True, "message": "更新成功"})

    elif request.method == "DELETE":
        cursor.execute("DELETE FROM [DataFormat] WHERE [FmtID] = ?", (fmt_id,))
        conn.commit()
        return jsonify({"ok": True, "message": "刪除成功"})



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

    formats = formats_info()
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
