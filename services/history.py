import os
import shutil
import datetime
import zipfile
import stat
import io
from flask import Blueprint, render_template, session, redirect, url_for, flash, jsonify, send_file, request
from modules.db import get_conn
from services.auth import login_required

history_bp = Blueprint('history', __name__)

def remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree to handle read-only files on Windows.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _should_include_result_file(filename, original_filename=None):

    if not filename:
        return False
 
    if filename.startswith("Results_") and filename.endswith(".zip"):
        return False

    if filename.endswith("_working.xlsx"):
        return False

    if filename == "date_errors.json":
        return False

    if filename.endswith("_Clean.xlsx") or filename.endswith("_Report.xlsx"):
        return True

    if original_filename and filename == original_filename:
        return True

    if original_filename:
        original_base, _ = os.path.splitext(original_filename)
        file_base, file_ext = os.path.splitext(filename)

        if file_base == original_base and file_ext.lower() in [".txt", ".xls", ".xlsx"]:
            return True

    return False

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
        shutil.rmtree(row[0], onerror=remove_readonly)      
    cursor.execute("DELETE FROM [Job] WHERE [JobID] = ? AND [UserID] = ?", (job_id, user_id))
    conn.commit()
    conn.close()
    flash("紀錄已成功刪除", "success")
    return redirect(url_for("history.history"))

@history_bp.route("/history/batch_delete", methods=["POST"])
@login_required
def batch_delete_history():
    user_id = session.get("id")
    data = request.json
    job_ids = data.get("job_ids", [])
    if not job_ids:
        return jsonify({"ok": False, "error": "未提供選取的項目"})

    conn = get_conn()
    cursor = conn.cursor()
    for job_id in job_ids:
        cursor.execute("SELECT [Path] FROM [Job] WHERE [JobID]=? AND [UserID]=?", (job_id, user_id))
        row = cursor.fetchone()
        if row and row[0] and os.path.exists(row[0]):
            shutil.rmtree(row[0], onerror=remove_readonly)
        cursor.execute("DELETE FROM [Job] WHERE [JobID] = ? AND [UserID] = ?", (job_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@history_bp.route("/history/detail/<job_id>")
@login_required
def detail_history(job_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.JobID,DataFormat.FmtName,DataFormat.Version,Job.TotalCount,Job.CompletenessScore,Job.CorrectScore,Job.ConsistencyScore,Job.DQI,Job.Path,Job.CreatedAt
                      FROM DataFormat RIGHT JOIN Job ON DataFormat.FmtID = Job.FmtID WHERE Job.JobID = ?""", (job_id,))
    row = cursor.fetchone()
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
        original_filename = row[1]
        zip_path = os.path.join(project_path, f"Results_{job_id}.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(project_path):
                for file in files:
                    if not _should_include_result_file(file, original_filename):
                        continue

                    file_path = os.path.join(root, file)
                    if not os.path.isfile(file_path):
                        continue

                    zipf.write(file_path, file)
        
        return send_file(os.path.abspath(zip_path), as_attachment=True)
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500

@history_bp.route("/history/batch_download", methods=["POST"])
@login_required
def batch_download_history():
    user_id = session.get("id")
    data = request.json
    job_ids = data.get("job_ids", [])
    
    if not job_ids:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT JobID FROM Job WHERE UserID = ?", (user_id,))
        job_ids = [r[0] for r in cursor.fetchall()]
        conn.close()
    if not job_ids:
        return jsonify({"ok": False, "error": "目前無任何紀錄可下載"})

    conn = get_conn()
    cursor = conn.cursor()
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for job_id in job_ids:
            cursor.execute("SELECT [Path], [FileName] FROM [Job] WHERE [JobID]=? AND [UserID]=?", (job_id, user_id))
            row = cursor.fetchone()
            if row and row[0] and os.path.exists(row[0]):
                project_path = row[0]
                folder_name = f"Job_{job_id}"
                original_filename = row[1]
                for root, dirs, files in os.walk(project_path):
                    for file in files:
                        if not _should_include_result_file(file, original_filename):
                            continue

                        file_path = os.path.join(root, file)
                        if not os.path.isfile(file_path):
                            continue

                        rel_path = os.path.join(folder_name, file)
                        zipf.write(file_path, rel_path)
    conn.close()
    memory_file.seek(0)
    return send_file(memory_file,mimetype='application/zip',as_attachment=True,download_name=f"Batch_Download_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.zip")
