import datetime
from flask import Flask, render_template, request, redirect, send_file, session, url_for, flash, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from modules.db import get_conn 
from modules.clean import cleanValidate
import shutil
from functools import wraps
import zipfile
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.handlers = []
werkzeug_logger.propagate = True

app = Flask(__name__)
BASE_DIR = os.path.dirname(__file__)
app.secret_key = "your_secret_key"
Jobs_FOLDER = 'static/Jobs'
os.makedirs(Jobs_FOLDER, exist_ok=True)
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"csv","xls","xlsx","txt"}

@app.context_processor
def inject_nav():
    NAV_ITEMS = [
        {"endpoint":"clean","title":"資料清洗模組","icon":"bi-funnel"},
        {"endpoint":"history","title":"資料審核紀錄","icon":"bi-file-earmark-text"},
        {"endpoint":"analytics","title":"統計分析","icon":"bi-bar-chart"},
        {"endpoint":"settings","title":"系統設定","icon":"bi-gear"},
    ]
    if session.get("position") == "Admin":
        NAV_ITEMS.append({"endpoint":"member", "title": "使用者管理", "icon": "bi-people"})
    return {"nav_items": NAV_ITEMS}

# ---- 登入驗證 ----
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ---- 管理員權限驗證 ----
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("position") != "Admin":
            flash("權限不足，無法存取此頁面", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function

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
        cursor.execute("SELECT [ID], [UserID], [Password], [Name], [Position], [Location] FROM [dbo].[Users] WHERE UserID = ? AND Password = ?", (user_id, password))
        user = cursor.fetchone()
        if user:
            logging.info(f"使用者 {user_id} 登入成功")
            session["id"] = str(user.ID)
            session["userid"] = user.UserID
            session["name"] = user.Name
            session["position"] = user.Position
            session["location"] = user.Location
            cursor.execute("UPDATE [dbo].[Users] SET Last_login = GETDATE() WHERE ID = ?", (user.ID,))
            conn.commit()
            conn.close()
            return redirect("/")
        conn.close()
        return render_template("login.html", error="帳號或密碼錯誤")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---- 使用者管理(Admin) ----------------------------
@app.route("/member")
@login_required
@admin_required
def member():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [ID], [UserID], [Password], [Name], [Position], [Location], [Last_login] FROM [dbo].[Users] ORDER BY UserID")
    columns = [column[0] for column in cursor.description]
    users = [dict(zip(columns, row)) for row in cursor.fetchall()]
    for u in users:
        u['ID'] = str(u['ID'])
        if u['Last_login'] and isinstance(u['Last_login'],datetime.datetime):
            u['Last_login'] = u['Last_login'].strftime("%Y/%m/%d %H:%M:%S")
    conn.close()
    return render_template("member.html", active="member", users=users)

@app.route("/member/tool", methods=["POST"])
@login_required
@admin_required
def admin_save_user():
    user_db_id = request.form.get("id")
    user_id = request.form.get("UserID")
    password = request.form.get("Password")
    name = request.form.get("Name")
    position = request.form.get("Position")
    location = request.form.get("Location")

    conn = get_conn()
    cursor = conn.cursor()
    if user_db_id:
        cursor.execute("UPDATE [dbo].[Users] SET [UserID]=?, [Password]=?, [Name]=?, [Position]=?, [Location]=? WHERE [ID]=?", (user_id, password, name, position, location, user_db_id))
        flash(f"使用者 {name} 資料已更新", "success")
    else:
        cursor.execute("INSERT INTO [dbo].[Users] ([UserID], [Password], [Name], [Position], [Location]) VALUES (?, ?, ?, ?, ?)", (user_id, password, name, position, location))
        flash(f"成功新增使用者 {name}", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("member"))

@app.route("/member/delete/<user_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Users] WHERE [ID]=?", (user_id,))
    conn.commit()
    conn.close()
    flash("使用者已成功刪除", "success")
    return redirect(url_for("member"))

# ---- 歷史紀錄 ------------------------------------------
@app.route("/history")
@login_required
def history():
    user_id = session.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.JobID,Job.UserID,DataFormat.FmtName,DataFormat.Version,Job.DQI,Job.CreatedAt,Job.TotalCount 
                      FROM DataFormat RIGHT JOIN Job ON DataFormat.FmtID = Job.FmtID
                      WHERE Job.UserID = ? ORDER BY Job.CreatedAt DESC""", (user_id,))
    history_data = []
    for row in cursor.fetchall():
        history_data.append({
            "JobID": row.JobID, "UserID": row.UserID, "FmtName": row.FmtName, "Version": row.Version,
            "DQI": f"{row.DQI:.2f}%", "CreatedAt": row.CreatedAt.strftime("%Y/%m/%d") if row.CreatedAt else "—", "TotalCount": row.TotalCount
        })
    conn.close()
    return render_template("history.html", active="history", history=history_data)

@app.route("/history/delete/<job_id>", methods=["POST"])
@login_required
def delete_history(job_id):
    user_id = session.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [Path] FROM [Job] WHERE [JobID]=? AND [UserID]=?", (job_id, user_id))
    row = cursor.fetchone()
    if row and row[0] and os.path.exists(row[0]): shutil.rmtree(row[0]) 
    cursor.execute("DELETE FROM [Job] WHERE [JobID] = ? AND [UserID] = ?", (job_id, user_id))
    conn.commit()
    conn.close()
    flash("紀錄已成功刪除", "success")
    return redirect("/history")

@app.route("/history/detail/<job_id>")
@login_required
def detail_history(job_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.JobID,DataFormat.FmtName,DataFormat.Version,Job.TotalCount,Job.CompletenessScore,Job.CorrectScore,Job.ConsistencyScore,Job.DQI,Job.Path,Job.CreatedAt
                      FROM DataFormat RIGHT JOIN Job ON DataFormat.FmtID = Job.FmtID WHERE Job.JobID = ?""", (job_id,))
    row = cursor.fetchone()
    if not row: return jsonify({"ok": False, "error": "找不到資料"}), 404
    data = dict(zip([c[0] for c in cursor.description], row))
    if isinstance(data['CreatedAt'], datetime.datetime): data['CreatedAt'] = data['CreatedAt'].strftime("%Y/%m/%d %H:%M:%S")
    conn.close()
    return jsonify({"ok": True, "data": data})

# ---- 資料清洗 ------------------------------------------
@app.route("/clean")
@login_required
def clean():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [FmtID], [FmtName], [Version], [Revision_date] FROM [DataFormat] ORDER BY FmtName ASC")
    formats = [{"id": str(r.FmtID), "name": str(r.FmtName), "version": str(r.Version), "updated": str(r.Revision_date)} for r in cursor.fetchall()]
    conn.close()
    return render_template("clean.html", active="clean", formats=formats)

@app.route("/api/formats", methods=["POST"])
@login_required
def api_add_format():
    if request.is_json:
        data = request.json
    else:
        data = request.form
    name, version, updated = data.get("name"), data.get("version"), data.get("updated")
    if not name or not version: return jsonify({"ok": False, "message": "名稱與版本為必填"}), 400
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO [DataFormat] ([FmtName], [Version], [Revision_date]) VALUES (?, ?, ?)", (name, version, updated))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/formats/<fmt_id>", methods=["PUT", "DELETE", "POST"])
@login_required
def api_manage_format(fmt_id):
    conn = get_conn()
    cursor = conn.cursor()

    if request.method == "DELETE":
        cursor.execute("DELETE FROM [DataFormat] WHERE [FmtID] = ?", (fmt_id,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})

    if request.is_json:
        data = request.json
    else:
        data = request.form
        
    name, version, updated = data.get("name"), data.get("version"), data.get("updated")
    cursor.execute("UPDATE [DataFormat] SET [FmtName]=?, [Version]=?, [Revision_date]=? WHERE [FmtID]=?", (name, version, updated, fmt_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/cleanJob", methods=["POST"])
@login_required
def api_clean():
    user_id, format_id = session.get("id"), request.form.get("format_id")
    uploaded_file = request.files.get("data_file")
    if not format_id or not uploaded_file or uploaded_file.filename == '': return jsonify({"ok": False, "error": "未選擇檔案"}), 400
    JobID = str(uuid.uuid4())
    project_folder = f"{Jobs_FOLDER}/{JobID}"
    os.makedirs(project_folder, exist_ok=True)

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [FmtName], [Version], [Revision_date] FROM [DataFormat] WHERE [FmtID] = ?", (format_id,))
    fmt_name, version, rev_date = cursor.fetchone()
    filename = secure_filename(uploaded_file.filename)
    path = f"{project_folder}/{filename}"
    uploaded_file.save(path)
    base_name = os.path.splitext(filename)[0]
    out_path, rep_path = f"{project_folder}/fmt{fmt_name}_{base_name}_clean.xlsx", f"{project_folder}/Report_{base_name}.xlsx"
    stats, alias_mapping, sorted_df, sorted_mask = cleanValidate(path, out_path, rep_path, f"fmt_{fmt_name}", version, rev_date)
    cursor.execute("INSERT INTO Job ([JobID],[UserID],[FmtID],[FileName],[TotalCount],[CompletenessScore],[CorrectScore],[ConsistencyScore],[DQI],[Path]) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (JobID, user_id, format_id, filename, int(stats['total']), float(stats['completeness']), float(stats['correctness']), float(stats['consistency']), float(stats['quality_score']), project_folder))
    conn.commit()
    conn.close()
    by_field = []
    for col in sorted_mask.columns:
        err_count = (sorted_mask[col] != "").sum()
        if err_count > 0:
            by_field.append({"name": col,"format": "檢核不符","errors": int(err_count)})
    
    by_type = [
        {"type": "A:遺漏值", "count": int(stats['missing_cells']), "ratio": f"{(stats['missing_cells']/(stats['total']*len(sorted_mask.columns))*100):.1f}%" if stats['total'] > 0 else "0%"},
        {"type": "B:格式不符", "count": int(stats['format_cells']), "ratio": f"{(stats['format_cells']/(stats['total']*len(sorted_mask.columns))*100):.1f}%" if stats['total'] > 0 else "0%"},
        {"type": "C:邏輯錯誤", "count": int(stats['logic_cells']), "ratio": f"{(stats['logic_cells']/(stats['total']*len(sorted_mask.columns))*100):.1f}%" if stats['total'] > 0 else "0%"}
    ]

    output_fields = [{"key": col, "label": col} for col in sorted_df.columns if not col.startswith('_')]
    return jsonify({
        "ok": True, 
        "project_id": JobID,
        "stats": {"total":int(stats['total']), "passed":int(stats['total']-stats['error_rows']), "error":int(stats['error_rows']), "completeness":float(stats['completeness']), "correctness":float(stats['correctness']), "dqi":float(stats['quality_score'])},
        "analysis": {"by_field": by_field,"by_type": by_type},
        "output_fields": output_fields
    })


@app.route("/api/download/<file_type>/<job_id>")
@login_required
def download_file(file_type, job_id):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT Job.Path, Job.FileName, DataFormat.FmtName FROM [Job] JOIN [DataFormat] ON Job.FmtID = DataFormat.FmtID WHERE Job.JobID=?", (job_id,))
        row = cursor.fetchone()
        if not row: return jsonify({"ok": False, "error": "找不到該紀錄"}), 404
        project_path, original_filename, fmt_name = row
        base_name, _ = os.path.splitext(original_filename)
        target_filename = f"fmt{fmt_name}_{base_name}_clean.xlsx" if file_type == "cleaned" else f"Report_{base_name}.xlsx"
        file_path = os.path.join(project_path, target_filename)
        conn.close()
        if not os.path.exists(file_path): 
            return jsonify({"ok": False, "error": "檔案不存在"}), 404
        return send_file(os.path.abspath(file_path), as_attachment=True)
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/history/download/<job_id>")
@login_required
def history_download_zip(job_id):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT Path, FileName FROM Job WHERE JobID=?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]: return jsonify({"ok": False, "error": "找不到該紀錄"}), 404
        
        project_path = row[0]
        zip_path = f"{project_path}/{f"AuditResults_{job_id}.zip"}"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    if file.endswith('.xlsx'): 
                        zipf.write(os.path.join(root, file), file)
        
        return send_file(os.path.abspath(zip_path), as_attachment=True)
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500








# ---- other ------------------------------------------
@app.route("/analytics")
@login_required
def analytics(): return render_template("analytics.html", active="analytics")

@app.route("/settings")
@login_required
def settings(): return render_template("settings.html", active="settings")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)