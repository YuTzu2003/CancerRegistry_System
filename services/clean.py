import os
import uuid
import csv
from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from modules.db import get_conn
from modules.cleaner import cleanValidate
from services.auth import login_required

clean_bp = Blueprint('clean', __name__)
Jobs_FOLDER = 'static/Jobs'

def load_field_spec(fmt_val):
    conn = get_conn()
    cursor = conn.cursor()
    sql = "SELECT [ChineseName], [Start], [End] FROM CancerRegistry_Fields WHERE [fmt]=? ORDER BY [Start]"
    cursor.execute(sql, fmt_val)
    rows = cursor.fetchall()
    conn.close()
    field_spec = [(r[0], int(r[1]), int(r[2])) for r in rows]
    return field_spec

def parse_fixed_width_line(line_text, spec):
    line_bytes = line_text.encode('big5', errors='ignore')
    parsed_row = {}
    for name, start, end in spec:
        field_value = line_bytes[start - 1:end]
        try:
            parsed_row[name] = field_value.decode('big5').strip()
        except:
            parsed_row[name] = field_value.decode('big5', errors='replace').strip()
    return parsed_row

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
    fmt_data = cursor.fetchone()
    if not fmt_data:
        conn.close()
        return jsonify({"ok": False, "error": "找不到指定的格式"}), 400
        
    fmt_name, version, rev_date = fmt_data
    
    filename = secure_filename(uploaded_file.filename)
    path = f"{project_folder}/{filename}"
    uploaded_file.save(path)
    uploaded_file.close()
    
    file_ext = os.path.splitext(filename)[1].lower()
    process_path = path

    if file_ext == '.txt':
        try:
            fmt_val = str(fmt_name).replace("fmt_", "")
            cursor.execute("SELECT MAX([End]) FROM CancerRegistry_Fields WHERE [fmt]=? GROUP BY [fmt]", (fmt_val,))
            row = cursor.fetchone()
            expected_length = row[0] if row else 0

            with open(path, 'r', encoding='big5', errors='ignore') as f:
                for i, line in enumerate(f):
                    clean_line = line.rstrip('\n').rstrip('\r')
                    # if not clean_line.strip(): continue
                    length = len(clean_line.encode('big5', errors='ignore'))
                    if expected_length > 0 and length != expected_length:
                        conn.close()
                        return jsonify({"ok": False, "error": f"第 {i} 行長度不符: 實際 {length}, 預期 {expected_length}"}), 400

            field_spec = load_field_spec(fmt_val)
            results = []
            with open(path, 'r', encoding='big5', errors='ignore') as f:
                for line in f:
                    # clean_line = line.rstrip('\n').rstrip('\r')
                    # if not clean_line.strip(): continue
                    results.append(parse_fixed_width_line(line, field_spec))

            temp_xlsx = f"{project_folder}/temp.xlsx"
            keys = [f[0] for f in field_spec]
            wb_temp = Workbook()
            ws_temp = wb_temp.active
            ws_temp.append(keys)

            for row_dict in results:
                row_values = [row_dict.get(k, "") for k in keys]
                ws_temp.append(row_values)
            for row in ws_temp.iter_rows():
                for cell in row:
                    cell.number_format = '@'
            
            wb_temp.save(temp_xlsx)
            process_path = temp_xlsx
            
        except Exception as e:
            conn.close()
            return jsonify({"ok": False, "error": f"TXT 解析失敗: {str(e)}"}), 500

    base_name = os.path.splitext(filename)[0]
    out_path, rep_path = f"{project_folder}/fmt{fmt_name}_{base_name}_clean.xlsx", f"{project_folder}/Report_{base_name}.xlsx"
    
    try:
        stats, alias_mapping, sorted_df, sorted_mask = cleanValidate(process_path, out_path, rep_path, f"fmt_{fmt_name}", version, rev_date)
        
        cursor.execute("INSERT INTO Job ([JobID],[UserID],[FmtID],[FileName],[TotalCount],[CompletenessScore],[CorrectScore],[ConsistencyScore],[DQI],[Path]) VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (JobID, user_id, format_id, filename, int(stats['total']), float(stats['completeness']), float(stats['correctness']), float(stats['consistency']), float(stats['quality_score']), project_folder))
        conn.commit()
    except Exception as e:
        if conn and not conn.closed: conn.rollback()
        return jsonify({"ok": False, "error":str(e)}), 500
    finally: 
        if conn and not conn.closed:
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
        "stats": {
            "total": int(stats['total']), 
            "passed": int(stats['total'] - stats['error_rows']), 
            "error": int(stats['error_rows']), 
            "completeness": float(stats['completeness']), 
            "correctness": float(stats['correctness']), 
            "consistency": float(stats['consistency']),
            "dqi": float(stats['quality_score'])
        },
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
        
        if file_type == "cleaned":
            target_filename = f"fmt{fmt_name}_{base_name}_clean.xlsx"
        elif file_type == "report":
            target_filename = f"Report_{base_name}.xlsx"
        elif file_type == "original":
            target_filename = original_filename
        else:
            return jsonify({"ok": False, "error": "無效的下載類型"}), 400

        file_path = os.path.join(project_path, target_filename)
        conn.close()
        if not os.path.exists(file_path): 
            return jsonify({"ok": False, "error": "檔案不存在"}), 404
        return send_file(os.path.abspath(file_path), as_attachment=True)
    except Exception as e: return jsonify({"ok": False, "error": str(e)}), 500