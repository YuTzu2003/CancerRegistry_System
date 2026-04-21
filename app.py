from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import os
import json
import uuid
from werkzeug.utils import secure_filename
from modules.db import get_conn 
from modules.clean import cleanValidate

app = Flask(__name__)
# ---- Config ---------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
# UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
# DATA_FOLDER = os.path.join(BASE_DIR, "data")
app.secret_key = "your_secret_key"
Jobs_FOLDER = 'static/Jobs'
os.makedirs(Jobs_FOLDER, exist_ok=True)
app.config["MAX_CONTENT_LENGTH"] = 32*1024*1024  #32MB
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"csv","xls","xlsx","txt"}

@app.context_processor
def inject_nav():
    NAV_ITEMS = [
                {"endpoint":"dashboard",     "title": "首頁總覽",    "icon": "bi-house-door"},
                {"endpoint":"data_cleaning", "title": "資料清洗模組","icon": "bi-funnel"},
                {"endpoint":"reports",       "title": "申報紀錄",    "icon": "bi-file-earmark-text"},
                {"endpoint":"analytics",     "title": "統計分析",    "icon": "bi-bar-chart"},
                {"endpoint":"settings",      "title": "系統設定",    "icon": "bi-gear"},]
    return {"nav_items": NAV_ITEMS}

# ---- Pages ----------------------------------------------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html", active="dashboard")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form["userid"]
        password = request.form["password"]
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""SELECT [ID], [UserID], [Password], [Name], [Position], [Location], [Last_login] FROM [dbo].[Users] WHERE UserID = ? AND Password = ?""", (user_id, password))
        user = cursor.fetchone()

        if user:
            session["id"] = str(user.ID)
            session["userid"] = user.UserID
            session["name"] = user.Name
            session["position"] = user.Position
            session["location"] = user.Location
            cursor.execute("""UPDATE [dbo].[Users] SET Last_login = GETDATE() WHERE ID = ? """, (user.ID,))
            conn.commit()
            return redirect("/")
        return render_template("login.html", error="帳號或密碼錯誤")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/reports")
def reports():
    return render_template("reports.html", active="reports")
@app.route("/analytics")
def analytics():
    return render_template("analytics.html", active="analytics")
@app.route("/settings")
def settings():
    return render_template("settings.html", active="settings")

# ---- format -------------------------------------------
@app.route("/clean")
def data_cleaning():
    formats = []
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT [FmtID], [FmtName], [Version], [Revision_date] FROM [DataFormat] ORDER BY FmtName ASC""")
    rows = cursor.fetchall()
    for row in rows:
        formats.append({"id": str(row.FmtID), "name": str(row.FmtName), "version": str(row.Version), "updated": str(row.Revision_date)})
    return render_template("clean.html",active="data_cleaning",formats=formats)

@app.route("/api/formats", defaults={"fmt_id": None}, methods=["POST"])
@app.route("/api/formats/<fmt_id>", methods=["PUT", "DELETE"])
def formatTool(fmt_id):
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



# @app.route("/api/cleanJob", methods=["POST"])
# def api_clean():
#     format_id = request.form.get("format_id")
#     uploaded_file = request.files.get("data_file")

#     if not format_id or not uploaded_file or uploaded_file.filename == '':
#         return jsonify({"ok": False, "error": "參數錯誤或未選擇檔案"}), 400

#     conn = get_conn()
#     cursor = conn.cursor()
#     cursor.execute("SELECT [FmtName], [Version], [Revision_date] FROM [DataFormat] WHERE [FmtID] = ?", (format_id,))
#     fmt_row = cursor.fetchone()
    
#     fmt, version, revision_date = fmt_row[0], fmt_row[1], fmt_row[2]
#     safe_filename = secure_filename(uploaded_file.filename)
#     input_path = os.path.join(Jobs_FOLDER, safe_filename)
#     uploaded_file.save(input_path)
#     output_path = os.path.join(Jobs_FOLDER, f"fmt{fmt}_{safe_filename}.xlsx")

#     stats, alias_mapping, sorted_df, sorted_mask = cleanValidate(
#         input_file=input_path,
#         output_file=output_path,
#         fmt=f"fmt_{fmt}",
#         version=version,
#         Revision_Date=revision_date
#     )

#     # 5. 將結果整理成前端 UI 需要的 JSON 格式
#     return jsonify({
#         "ok": True,
#         "message": "資料清洗完成！",
#         "stats": {
#             "total": int(stats['total']),
#             "passed": int(stats['total'] - stats['error_rows']),
#             "error": int(stats['error_rows']),
#             "dqi": float(stats['quality_score'])
#         },
#         # 這裡把檔案名稱也傳給前端，方便後續實作「下載報表」功能
#         "files": {
#             "cleaned_data": output_path,
#             "report": f"Report_{os.path.splitext(safe_filename)[0]}.xlsx"
#         }
#     })
import os
import uuid
from flask import request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime

@app.route("/api/cleanJob", methods=["POST"])
def api_clean():
    user_id = session.get("id")
    if not user_id:
        return jsonify({"ok": False, "error": "請先登入系統"}), 401

    format_id = request.form.get("format_id")
    uploaded_file = request.files.get("data_file")

    if not format_id or not uploaded_file or uploaded_file.filename == '':
        return jsonify({"ok": False, "error": "未選擇檔案"}), 400

    JobID = str(uuid.uuid4())
    project_folder = f"{Jobs_FOLDER}/{JobID}"
    os.makedirs(project_folder, exist_ok=True)

    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT [FmtName], [Version], [Revision_date] FROM [DataFormat] WHERE [FmtID] = ?", (format_id,))
        fmt_row = cursor.fetchone()
        
        fmt_name, version, revision_date = fmt_row[0], fmt_row[1], fmt_row[2]
        filename = secure_filename(uploaded_file.filename)
        path = f"{project_folder}/{filename}"
        uploaded_file.save(path)
        output_filename = f"fmt{fmt_name}_{filename}.xlsx"
        output_path = f"{project_folder}, {output_filename}"

        stats, alias_mapping, sorted_df, sorted_mask = cleanValidate(path, output_path, f"fmt_{fmt_name}", version, revision_date)

        sql = """INSERT INTO Job ([JobID],[UserID],[FileName],[TotalCount],[CompletenessScore],[CorrectScore],[ConsistencyScore],[DQI],[Path]) VALUES (?,?,?,?,?,?,?,?,?)"""
        cursor.execute(sql, (JobID, user_id, filename, int(stats['total']), float(stats['completeness']), float(stats['correctness']), float(stats['consistency']), float(stats['quality_score']),path))
        conn.commit()

        return jsonify({
            "ok": True,
            "project_id": JobID,
            "message": "資料清洗並存檔完成！",
            "stats": {
                "total": int(stats['total']),
                "passed": int(stats['total'] - stats['error_rows']),
                "error": int(stats['error_rows']),
                "dqi": float(stats['quality_score'])
            },
            "files": {
                "project_dir": JobID,
                "cleaned_data": output_filename,
                "report": f"Report_{os.path.splitext(filename)[0]}.xlsx"
            }
        })

    except Exception as e:
        print(f"清洗專案 {JobID} 發生錯誤: {str(e)}")
        return jsonify({"ok": False, "error": f"系統處理失敗: {str(e)}"}), 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)