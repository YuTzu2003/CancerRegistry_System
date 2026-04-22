import datetime
from flask import Flask, render_template, request, redirect, send_file, session, url_for, flash, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from modules.db import get_conn 
from modules.clean import cleanValidate
import shutil
from functools import wraps

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
app.secret_key = "your_secret_key"

# ---- 登入驗證裝飾器 ----
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "id" not in session:
            flash("請先登入系統", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

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
                {"endpoint":"history",       "title": "資料審核紀錄",    "icon": "bi-file-earmark-text"},
                {"endpoint":"analytics",     "title": "統計分析",    "icon": "bi-bar-chart"},
                {"endpoint":"settings",      "title": "系統設定",    "icon": "bi-gear"},]
    return {"nav_items": NAV_ITEMS}

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", active="dashboard")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "id" in session:
        return redirect(url_for("dashboard"))

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
            session.pop('_flashes', None)
            
            return redirect("/")
        return render_template("login.html", error="帳號或密碼錯誤")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/history")
@login_required
def history():
    user_id = session.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""  SELECT Job.JobID,Job.UserID,DataFormat.FmtName,DataFormat.Version,Job.DQI,Job.CreatedAt,Job.TotalCount 
                        FROM DataFormat RIGHT  JOIN Job ON DataFormat.FmtID = Job.FmtID
                        WHERE Job.UserID = ?
                        ORDER BY Job.CreatedAt DESC """,(user_id,))
    rows = cursor.fetchall()
    history_data = []
    for row in rows:
        history_data.append({
            "JobID": row.JobID,
            "UserID": row.UserID,
            "FmtName": row.FmtName,
            "Version": row.Version,
            "DQI": f"{row.DQI:.2f}%",
            "CreatedAt": row.CreatedAt.strftime("%Y/%m/%d") if row.CreatedAt else "—",
            "TotalCount": row.TotalCount
        })
    return render_template("history.html", active="history", history=history_data)

@app.route("/history/delete/<job_id>", methods=["POST"])
@login_required
def delete_history(job_id):
    user_id = session.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    
    cursor.execute("SELECT [Path] FROM [Job] WHERE [JobID]=? AND [UserID]=?", (job_id,user_id))
    row = cursor.fetchone()
    
    if row and row[0]:
        target_path = row[0]
        if os.path.exists(target_path):
            shutil.rmtree(target_path) 
    cursor.execute("DELETE FROM [Job] WHERE [JobID] = ? AND [UserID] = ?", (job_id, user_id))
    conn.commit()
    
    flash("紀錄已成功刪除", "success")
    conn.close()  
    return redirect("/history")

@app.route("/history/detail/<job_id>", methods=["GET"])
@login_required
def detail_history(job_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(""" SELECT Job.JobID,DataFormat.FmtName,DataFormat.Version,Job.TotalCount,Job.CompletenessScore,Job.CorrectScore,Job.ConsistencyScore,Job.DQI,Job.Path,Job.CreatedAt
                        FROM DataFormat RIGHT JOIN Job ON DataFormat.FmtID = Job.FmtID
                        WHERE Job.JobID = ? """, (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "找不到資料"}), 404
    columns = [column[0] for column in cursor.description]
    data = dict(zip(columns, row))
    if data.get('CreatedAt'):
        if isinstance(data['CreatedAt'], datetime.datetime):
            data['CreatedAt'] = data['CreatedAt'].strftime("%Y/%m/%d %H:%M:%S")
    return jsonify({"ok": True, "data": data})

@app.route("/history/download/<job_id>")
@login_required
def download_project(job_id):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT [Path], [FileName] FROM [Job] WHERE [JobID] = ?", (job_id,))
        row = cursor.fetchone()
        project_path = row[0]
        zip_temp_path = os.path.join(os.path.dirname(project_path), f"{job_id}.zip")
        shutil.make_archive(zip_temp_path.replace('.zip', ''), 'zip', project_path)
        return send_file(zip_temp_path, as_attachment=True, download_name=f"{job_id}.zip")
    except Exception as e:
        return {str(e)}, 500

@app.route("/api/download/<file_type>/<job_id>")
@login_required
def download_file(file_type, job_id):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Job.JobID, Job.Path, Job.FileName, DataFormat.FmtName 
            FROM [Job] 
            JOIN [DataFormat] ON Job.FmtID = DataFormat.FmtID 
            WHERE Job.JobID=?
        """, (job_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"ok": False, "error": "找不到該紀錄"}), 404
            
        project_path, original_filename, fmt_name = row
        base_name, _ = os.path.splitext(original_filename)
        
        if file_type == "cleaned":
            target_filename = f"fmt{fmt_name}_{base_name}_clean.xlsx"
        elif file_type == "report":
            target_filename = f"Report_{base_name}.xlsx"
        else:
            return jsonify({"ok": False, "error": "無效的下載類型"}), 400
            
        file_path = f"{project_path}/{target_filename}"
        conn.close()
        
        if not os.path.exists(file_path):
            return jsonify({"ok": False, "error": "檔案不存在"}), 404
            
        return send_file(os.path.abspath(file_path), as_attachment=True)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html", active="analytics")

@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", active="settings")

# ---- format -------------------------------------------
@app.route("/clean")
@login_required
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
@login_required
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

# ---------------------- clean ---------------------------------------------
@app.route("/api/cleanJob", methods=["POST"])
@login_required
def api_clean():
    user_id = session.get("id")
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
        base_name, _ = os.path.splitext(filename) 
        path = f"{project_folder}/{filename}"
        uploaded_file.save(path)
        
        output_filename = f"fmt{fmt_name}_{base_name}_clean.xlsx"
        output_path = f"{project_folder}/{output_filename}"
        report_filename = f"Report_{base_name}.xlsx"
        report_path = f"{project_folder}/{report_filename}"

        stats, alias_mapping, sorted_df, sorted_mask = cleanValidate(path, output_path, report_path, f"fmt_{fmt_name}", version, revision_date)
        sorted_df = sorted_df.fillna('')
        issues = []
        has_error_mask = sorted_mask.ne("").any(axis=1)
        error_indices = sorted_mask[has_error_mask].index[:100]
        id_col = next((c for c in sorted_df.columns if "編號" in c or "ID" in c.upper()), sorted_df.columns[0])
        
        for idx in error_indices:
            row_data = sorted_df.loc[idx]
            row_mask = sorted_mask.loc[idx]
            for col in sorted_mask.columns:
                err = row_mask[col]
                if err:
                    issues.append({
                        "case_id": str(row_data[id_col]),
                        "field": str(col),
                        "level": "error",
                        "type": "遺漏值" if err == "missing" else ("格式錯誤" if err == "format" else "邏輯錯誤"),
                        "value": str(row_data[col]),
                        "suggestion": "請補齊資料" if err == "missing" else "請檢查格式"
                    })
        
        by_field = []
        for col in sorted_mask.columns:
            err_count = (sorted_mask[col] != "").sum()
            if err_count > 0:
                by_field.append({"name": str(col), "format": "檢核規則", "errors": int(err_count)})
        
        total_cells = max(1, int(stats['total']) * len(sorted_mask.columns))
        by_type = [
            {"type": "遺漏值 (Missing)", "count": int(stats.get('missing_cells', 0)), "ratio": f"{(int(stats.get('missing_cells', 0))/total_cells):.1%}"},
            {"type": "格式錯誤 (Format)", "count": int(stats.get('format_cells', 0)), "ratio": f"{(int(stats.get('format_cells', 0))/total_cells):.1%}"},
            {"type": "邏輯錯誤 (Logic)", "count": int(stats.get('logic_cells', 0)), "ratio": f"{(int(stats.get('logic_cells', 0))/total_cells):.1%}"}
        ]

        output_fields = [{"key": str(col), "label": str(col)} for col in sorted_df.columns if not str(col).startswith('_')]
        sql = """INSERT INTO Job ([JobID],[UserID],[FmtID],[FileName],[TotalCount],[CompletenessScore],[CorrectScore],[ConsistencyScore],[DQI],[Path]) VALUES (?,?,?,?,?,?,?,?,?,?)"""
        cursor.execute(sql,(JobID, user_id, format_id, filename, int(stats['total']), float(stats['completeness']), float(stats['correctness']), float(stats['consistency']), float(stats['quality_score']), project_folder))
        conn.commit()

        return jsonify({
            "ok": True,
            "project_id": JobID,
            "message": "資料清洗並存檔完成！",
            "stats": {
                "total": int(stats['total']),
                "passed": int(stats['total'] - stats['error_rows']),
                "error": int(stats['error_rows']),
                "dqi": float(stats['quality_score']),
                "completeness": float(stats['completeness']),
                "correctness": float(stats['correctness'])
            },
            "issues": issues,
            "analysis": {"by_field": by_field,"by_type": by_type},
            "output_fields": output_fields,
            "files": {"project_dir": JobID,"cleaned_data": output_filename,"report": report_filename}
        })
    except Exception as e:
        return jsonify({"ok": False, "error": f"系統處理失敗: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
