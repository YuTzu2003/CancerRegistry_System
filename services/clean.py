import os
import uuid
from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename
from modules.db import get_conn
from modules.cleaner import cleanValidate
from services.auth import login_required

clean_bp = Blueprint('clean', __name__)
Jobs_FOLDER = 'static/Jobs'

@clean_bp.route("/clean")
@login_required
def clean():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [FmtID], [FmtName], [Version], [Revision_date] FROM [DataFormat] ORDER BY FmtName ASC")
    formats = [{"id": str(r.FmtID), "name": str(r.FmtName), "version": str(r.Version), "updated": str(r.Revision_date)} for r in cursor.fetchall()]
    conn.close()
    return render_template("clean.html", active="clean", formats=formats)

@clean_bp.route("/api/formats", methods=["POST"])
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

@clean_bp.route("/api/formats/<fmt_id>", methods=["PUT", "DELETE", "POST"])
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

@clean_bp.route("/api/cleanJob", methods=["POST"])
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

@clean_bp.route("/api/download/<file_type>/<job_id>")
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
