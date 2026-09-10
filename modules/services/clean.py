import datetime
import io
import os
import shutil
import stat
import zipfile

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from modules.services.auth import login_required, admin_required
from modules.blueprint.clean import categorize_fields_logic,export_logic,preview_logic,get_formats_logic,add_format_logic,manage_format_logic,clean_job_logic,get_date_errors_logic,update_date_error_logic,download_temp_file_logic,download_file_logic
from modules.services.db import get_conn

clean_bp = Blueprint('clean', __name__, template_folder='../blueprint/clean/templates')

@clean_bp.route("/api/categorize_fields", methods=["POST"])
@login_required
def api_categorize_fields():
    data = request.json
    res, status = categorize_fields_logic(data.get("job_id"), session.get("id"), data.get("scheme"))
    return jsonify(res), status

@clean_bp.route("/api/export", methods=["POST"])
@login_required
def api_export():
    data = request.json
    res, status = export_logic(data.get("job_id"), session.get("id"), data.get("scheme"), data.get("fields", []))
    if res.get("send_file"):
        resp = send_file(res["path"], as_attachment=True, download_name=res["download_name"])
        resp.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return resp
    return jsonify(res), status

@clean_bp.route("/api/preview", methods=["POST"])
@login_required
def api_preview():
    data = request.json
    res, status = preview_logic(data.get("job_id"), session.get("id"), data.get("scheme"), data.get("fields", []))
    return jsonify(res), status

@clean_bp.route("/clean")
@login_required
def clean():
    formats = get_formats_logic()
    return render_template("clean.html", active="clean", formats=formats)

@clean_bp.route("/api/formats", methods=["POST"])
@admin_required
def api_add_format():
    data = request.json if request.is_json else request.form
    res, status = add_format_logic(data.get("name"), data.get("version"), data.get("updated"))
    return jsonify(res), status

@clean_bp.route("/api/formats/<fmt_id>", methods=["PUT", "DELETE", "POST"])
@admin_required
def api_manage_format(fmt_id):
    data = request.json if request.is_json else request.form
    if request.method == "DELETE":
        res, status = manage_format_logic("DELETE", fmt_id, None, None, None)
    else:
        res, status = manage_format_logic("UPDATE", fmt_id, data.get("name"), data.get("version"), data.get("updated"))
    return jsonify(res), status

@clean_bp.route("/api/cleanJob", methods=["POST"])
@login_required
def api_clean():
    user_id = session.get("id")
    format_id = request.form.get("format_id")
    convert_txt_flag = request.form.get("convert_txt") == "true"
    uploaded_file = request.files.get("data_file")

    res, status = clean_job_logic(user_id, format_id, convert_txt_flag, uploaded_file)
    return jsonify(res), status

@clean_bp.route("/api/date_errors", methods=["POST"])
@login_required
def api_date_errors():
    data = request.get_json(silent=True) or {}
    res, status = get_date_errors_logic(data.get("job_id"), session.get("id"))
    return jsonify(res), status

@clean_bp.route("/api/date_errors/update", methods=["POST"])
@login_required
def api_update_date_error():
    data = request.get_json(silent=True) or {}
    res, status = update_date_error_logic(data.get("job_id"), session.get("id"), data.get("row_index"), data.get("updates"))
    return jsonify(res), status

@clean_bp.route("/api/download_temp/<file_type>/<temp_id>/<filename>")
@login_required
def download_temp_file(file_type, temp_id, filename):
    res, status = download_temp_file_logic(file_type, temp_id, filename)
    if res.get("send_file"):
        return send_file(res["path"], as_attachment=True, download_name=res["download_name"])
    return jsonify(res), status

@clean_bp.route("/api/download/<file_type>/<job_id>")
@login_required
def download_file(file_type, job_id):
    res, status = download_file_logic(file_type, job_id, session.get("id"))
    if res.get("send_file"):
        return send_file(res["path"], as_attachment=True, download_name=res["download_name"])
    return jsonify(res), status


# 清洗歷程頁面：顯示、管理與下載使用者的資料清洗作業結果。
def remove_readonly(func, path, excinfo):
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

@clean_bp.route("/clean/history")
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

@clean_bp.route("/clean/history/delete/<job_id>", methods=["POST"])
@login_required
def delete_history(job_id):
    user_id = session.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [Path] FROM [Job] WHERE [JobID]=? AND [UserID]=?", (job_id, user_id))
    row = cursor.fetchone()

    if row and row[0]:
        fixed_path = row[0].replace('work/', 'tasks/').replace('work\\', 'tasks\\')
        if os.path.exists(fixed_path):
            try:
                shutil.rmtree(fixed_path, onerror=remove_readonly)
            except Exception:
                pass
    cursor.execute("DELETE FROM [Job] WHERE [JobID] = ? AND [UserID] = ?", (job_id, user_id))
    conn.commit()
    conn.close()
    flash("紀錄已成功刪除", "success")
    return redirect(url_for("clean.history"))

@clean_bp.route("/clean/history/batch_delete", methods=["POST"])
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
        if row and row[0]:
            fixed_path = row[0].replace('work/', 'tasks/').replace('work\\', 'tasks\\')
            if os.path.exists(fixed_path):
                try:
                    shutil.rmtree(fixed_path, onerror=remove_readonly)
                except Exception:
                    pass
        cursor.execute("DELETE FROM [Job] WHERE [JobID] = ? AND [UserID] = ?", (job_id, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@clean_bp.route("/clean/history/detail/<job_id>")
@login_required
def detail_history(job_id):
    user_id = session.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.JobID,DataFormat.FmtName,DataFormat.Version,Job.TotalCount,Job.CompletenessScore,Job.CorrectScore,Job.ConsistencyScore,Job.DQI,Job.Path,Job.CreatedAt
                      FROM DataFormat RIGHT JOIN Job ON DataFormat.FmtID = Job.FmtID WHERE Job.JobID = ? AND Job.UserID = ?""", (job_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "找不到紀錄"}), 404
    data = dict(zip([c[0] for c in cursor.description], row))
    if isinstance(data['CreatedAt'], datetime.datetime):
        data['CreatedAt'] = data['CreatedAt'].strftime("%Y/%m/%d %H:%M:%S")
    conn.close()
    return jsonify({"ok": True, "data": data})

@clean_bp.route("/clean/history/download/<job_id>")
@login_required
def history_download_zip(job_id):
    try:
        user_id = session.get("id")
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT Path, FileName FROM Job WHERE JobID=? AND UserID=?", (job_id, user_id))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]: return jsonify({"ok": False, "error": "Not found"}), 404

        project_path = row[0].replace('work/', 'tasks/').replace('work\\', 'tasks\\')
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

@clean_bp.route("/clean/history/batch_download", methods=["POST"])
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
            if row and row[0]:
                project_path = row[0].replace('work/', 'tasks/').replace('work\\', 'tasks\\')
                if os.path.exists(project_path):
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