import datetime
import io
import json
import os
import shutil
import stat
import zipfile
from copy import copy
from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from openpyxl import load_workbook
from modules.services.auth import login_required, admin_required
from modules.blueprint.clean import categorize_fields_logic,export_logic,preview_logic,get_formats_logic,add_format_logic,manage_format_logic,clean_job_logic,get_date_errors_logic,update_date_error_logic,download_file_logic,get_review_records_logic
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

    res, status = clean_job_logic(user_id, format_id, convert_txt_flag, uploaded_file, request.form.getlist("review_job_ids"))
    return jsonify(res), status

@clean_bp.route("/api/review-records")
@login_required
def api_review_records():
    res, status = get_review_records_logic(session.get("id"))
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

@clean_bp.route("/api/download/<file_type>/<job_id>")
@login_required
def download_file(file_type, job_id):
    res, status = download_file_logic(file_type, job_id, session.get("id"))
    if res.get("send_file"):
        return send_file(res["path"], as_attachment=True, download_name=res["download_name"])
    return jsonify(res), status


@clean_bp.route("/api/download-clean-result/<job_id>")
@login_required
def download_clean_result(job_id):
    cleaned, status = download_file_logic("cleaned", job_id, session.get("id"))
    if not cleaned.get("send_file"):
        return jsonify(cleaned), status
    report, status = download_file_logic("report", job_id, session.get("id"))
    if not report.get("send_file"):
        return jsonify(report), status

    output = _build_combined_clean_result(cleaned["path"], report["path"])
    return send_file(output, as_attachment=True, download_name=cleaned["download_name"],
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _build_combined_clean_result(cleaned_path, report_path):
    workbook = load_workbook(cleaned_path)
    report_workbook = load_workbook(report_path)
    try:
        workbook.active.title = "清洗結果明細"
        source = report_workbook.active
        analysis = workbook.create_sheet("清洗結果分析", 0)
        for row in source.iter_rows():
            for cell in row:
                target = analysis.cell(row=cell.row, column=cell.column, value=cell.value)
                if cell.has_style:
                    target.font = copy(cell.font)
                    target.fill = copy(cell.fill)
                    target.border = copy(cell.border)
                    target.alignment = copy(cell.alignment)
                    target.number_format = cell.number_format
                    target.protection = copy(cell.protection)
        for key, dimension in source.column_dimensions.items():
            analysis.column_dimensions[key].width = dimension.width
        for key, dimension in source.row_dimensions.items():
            analysis.row_dimensions[key].height = dimension.height
        for merged_range in source.merged_cells.ranges:
            analysis.merge_cells(str(merged_range))
        workbook.active = 0
        output = io.BytesIO()
        workbook.save(output)
    finally:
        report_workbook.close()
        workbook.close()
    output.seek(0)
    return output


# 清洗歷程頁面：顯示、管理與下載使用者的資料清洗作業結果。
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _should_include_history_file(filename, original_filename=None):
    if not filename:
        return False
    if filename.startswith("Results_") and filename.endswith(".zip"):
        return False
    if filename.endswith("_working.xlsx") or filename == "date_errors.json":
        return False
    if filename.endswith("_Clean.xlsx") or filename.endswith("_Report.xlsx"):
        return False
    if original_filename and filename == original_filename:
        return True
    if original_filename:
        original_base, _ = os.path.splitext(original_filename)
        file_base, file_ext = os.path.splitext(filename)
        return file_base == original_base and file_ext.lower() in [".txt", ".xls", ".xlsx"]
    return False


def _add_history_files(zip_file, project_path, original_filename, fmt_name, folder_name=""):
    for root, _, files in os.walk(project_path):
        for filename in files:
            if not _should_include_history_file(filename, original_filename):
                continue
            file_path = os.path.join(root, filename)
            if os.path.isfile(file_path):
                zip_file.write(file_path, os.path.join(folder_name, filename))

    base_name, _ = os.path.splitext(original_filename)
    result_name = f"fmt{fmt_name}_{base_name}_Clean.xlsx"
    cleaned_path = os.path.join(project_path, result_name)
    report_path = os.path.join(project_path, f"fmt{fmt_name}_{base_name}_Report.xlsx")
    if os.path.exists(cleaned_path) and os.path.exists(report_path):
        zip_file.writestr(os.path.join(folder_name, result_name),
                          _build_combined_clean_result(cleaned_path, report_path).getvalue())


@clean_bp.route("/clean/history")
@login_required
def history():
    user_id = session.get("id")
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.JobID,Job.UserID,Job.FileName,DataFormat.FmtName,DataFormat.Version,Job.DQI,Job.CreatedAt,Job.TotalCount
                      FROM DataFormat RIGHT JOIN Job ON DataFormat.FmtID = Job.FmtID
                      WHERE Job.UserID = ? ORDER BY Job.CreatedAt DESC""", (user_id,))
    history_data = []
    for row in cursor.fetchall():
        history_data.append({"JobID": row.JobID, "ShortJobID": str(row.JobID)[-5:], "UserID": row.UserID, "FileName": row.FileName, "FmtName": row.FmtName, "Version": row.Version,"DQI": f"{row.DQI:.2f}%", "CreatedAt": row.CreatedAt.strftime("%Y/%m/%d") if row.CreatedAt else "—", "TotalCount": row.TotalCount})
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
    cursor.execute("""SELECT Job.JobID,Job.FileName,DataFormat.FmtName,DataFormat.Version,Job.TotalCount,Job.CompletenessScore,Job.CorrectScore,Job.ConsistencyScore,Job.DQI,Job.Path,Job.CreatedAt,Job.ExcludedReviewNames
                      FROM DataFormat RIGHT JOIN Job ON DataFormat.FmtID = Job.FmtID WHERE Job.JobID = ? AND Job.UserID = ?""", (job_id, user_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "找不到紀錄"}), 404
    data = dict(zip([c[0] for c in cursor.description], row))
    if isinstance(data['CreatedAt'], datetime.datetime):
        data['CreatedAt'] = data['CreatedAt'].strftime("%Y/%m/%d %H:%M:%S")
    data['ExcludedReviewNames'] = json.loads(data['ExcludedReviewNames']) if data['ExcludedReviewNames'] else []
    conn.close()
    return jsonify({"ok": True, "data": data})

@clean_bp.route("/clean/history/download/<job_id>")
@login_required
def history_download_zip(job_id):
    try:
        user_id = session.get("id")
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""SELECT Job.Path, Job.FileName, DataFormat.FmtName
                          FROM Job JOIN DataFormat ON Job.FmtID = DataFormat.FmtID
                          WHERE Job.JobID=? AND Job.UserID=?""", (job_id, user_id))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]: return jsonify({"ok": False, "error": "Not found"}), 404

        project_path = row[0].replace('work/', 'tasks/').replace('work\\', 'tasks\\')
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            _add_history_files(zip_file, project_path, row[1], row[2])
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=f"Results_{job_id}.zip",
                         mimetype="application/zip")
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
            cursor.execute("""SELECT Job.Path, Job.FileName, DataFormat.FmtName
                              FROM Job JOIN DataFormat ON Job.FmtID = DataFormat.FmtID
                              WHERE Job.JobID=? AND Job.UserID=?""", (job_id, user_id))
            row = cursor.fetchone()
            if row and row[0]:
                project_path = row[0].replace('work/', 'tasks/').replace('work\\', 'tasks\\')
                _add_history_files(zipf, project_path, row[1], row[2], f"Job_{job_id}")
    conn.close()
    memory_file.seek(0)
    return send_file(memory_file,mimetype='application/zip',as_attachment=True,download_name=f"Batch_Download_{datetime.datetime.now().strftime('%Y%m%d%H%M')}.zip")
