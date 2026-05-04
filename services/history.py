import os
import shutil
import datetime
import zipfile
import stat
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, send_file
from modules.db import get_conn
from services.auth import login_required

history_bp = Blueprint('history', __name__)

def remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree to handle read-only files on Windows.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)

@history_bp.route("/history")
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
        history_data.append({"JobID": row.JobID, "UserID": row.UserID, "FmtName": row.FmtName, "Version": row.Version,"DQI": f"{row.DQI:.2f}%", "CreatedAt": row.CreatedAt.strftime("%Y/%m/%d") if row.CreatedAt else "—", "TotalCount": row.TotalCount})
    conn.close()
    return render_template("history.html", active="history", history=history_data)

@history_bp.route("/history/delete/<job_id>", methods=["POST"])
@login_required
def delete_history(job_id):
    user_id = session.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [Path] FROM [Job] WHERE [JobID]=? AND [UserID]=?", (job_id, user_id))
    row = cursor.fetchone()
    
    if row and row[0] and os.path.exists(row[0]): 
        try:
            shutil.rmtree(row[0], onerror=remove_readonly)
        except Exception as e:
            print(f"Error deleting folder {row[0]}: {e}")
            
    cursor.execute("DELETE FROM [Job] WHERE [JobID] = ? AND [UserID] = ?", (job_id, user_id))
    conn.commit()
    conn.close()
    flash("紀錄已成功刪除", "success")
    return redirect(url_for("history.history"))

@history_bp.route("/history/detail/<job_id>")
@login_required
def detail_history(job_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.JobID,DataFormat.FmtName,DataFormat.Version,Job.TotalCount,Job.CompletenessScore,Job.CorrectScore,Job.ConsistencyScore,Job.DQI,Job.Path,Job.CreatedAt
                    FROM DataFormat RIGHT JOIN Job ON DataFormat.FmtID = Job.FmtID 
                    WHERE Job.JobID = ?""", (job_id,))
    row = cursor.fetchone()
    if not row: return jsonify({"ok": False, "error": "找不到資料"}), 404
    data = dict(zip([c[0] for c in cursor.description], row))
    if isinstance(data['CreatedAt'], datetime.datetime): 
        data['CreatedAt'] = data['CreatedAt'].strftime("%Y/%m/%d %H:%M:%S")
    conn.close()
    return jsonify({"ok": True, "data": data})

@history_bp.route("/history/download/<job_id>")
@login_required
def history_download_zip(job_id):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT Path, FileName FROM Job WHERE JobID=?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]: return jsonify({"ok": False, "error": "Not found"}), 404
        
        project_path = row[0]
        zip_path = os.path.join(project_path, f"Results_{job_id}.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    if file == f"Results_{job_id}.zip":
                        continue
                    zipf.write(os.path.join(root, file), file)
        
        return send_file(os.path.abspath(zip_path), as_attachment=True)
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500
