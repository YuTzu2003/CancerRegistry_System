import os
import uuid
import csv
from flask import Blueprint, render_template, request, session, jsonify, send_file
from werkzeug.utils import secure_filename
from modules.db import get_conn
from modules.cleaner import cleanValidate
from services.auth import login_required
from modules.field_mapping import detect_system, get_field_map
from openpyxl import load_workbook, Workbook
from openpyxl.utils import get_column_letter
from copy import copy

clean_bp = Blueprint('clean', __name__)
Jobs_FOLDER = 'static/Jobs'

def copy_cell(source_cell, target_cell):
    target_cell.value = source_cell.value
    if source_cell.has_style:
        target_cell.font = copy(source_cell.font)
        target_cell.border = copy(source_cell.border)
        target_cell.fill = copy(source_cell.fill)
        target_cell.number_format = copy(source_cell.number_format)
        target_cell.protection = copy(source_cell.protection)
        target_cell.alignment = copy(source_cell.alignment)

@clean_bp.route("/api/categorize_fields", methods=["POST"])
@login_required
def api_categorize_fields():
    data = request.json
    job_id = data.get("job_id")
    scheme = data.get("scheme")

    if not job_id or not scheme:
        return jsonify({"ok": False, "error": "參數不足"}), 400

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.Path, Job.FileName, DataFormat.FmtName FROM [Job] JOIN [DataFormat] ON Job.FmtID = DataFormat.FmtID WHERE Job.JobID=?""", (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "找不到該紀錄"}), 404

    project_path, original_filename, fmt_name = row
    base_name, _ = os.path.splitext(original_filename)
    cleaned_file = os.path.join(project_path, f"fmt{fmt_name}_{base_name}_Clean.xlsx")

    if not os.path.exists(cleaned_file):
        return jsonify({"ok": False, "error": "清洗檔案不存在"}), 404

    try:
        wb = load_workbook(cleaned_file, read_only=True)
        ws = wb.active
        headers = [cell.value for cell in next(ws.iter_rows(max_row=1))]
        wb.close()

        alias_to_target = get_field_map(scheme, fmt_name)
        mapped = []
        unmapped = []
        for h in headers:
            if h.startswith('_') or h == '錯誤註記說明(A:遺漏值 B:格式不符 C:邏輯錯誤 D:完全正確)':
                continue
            if h in alias_to_target:
                mapped.append({"key": h, "label": h, "target": alias_to_target[h]})
            else:
                unmapped.append({"key": h, "label": h})
        return jsonify({"ok": True,"mapped": mapped,"unmapped": unmapped})
    
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@clean_bp.route("/api/export", methods=["POST"])
@login_required
def api_export():
    data = request.json
    job_id = data.get("job_id")
    scheme = data.get("scheme")
    selected_fields = data.get("fields", [])
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""SELECT Job.Path, Job.FileName, DataFormat.FmtName FROM [Job] JOIN [DataFormat] ON Job.FmtID = DataFormat.FmtID WHERE Job.JobID=?""", (job_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"ok": False, "error": "找不到該紀錄"}), 404

    project_path, original_filename, fmt_name = row
    base_name, _ = os.path.splitext(original_filename)
    cleaned_file = os.path.join(project_path, f"fmt{fmt_name}_{base_name}_Clean.xlsx")

    if not os.path.exists(cleaned_file):
        return jsonify({"ok": False, "error": "清洗檔案不存在"}), 404

    alias_to_target = get_field_map(scheme, fmt_name)
    scheme_display = {
        "field_name_zh":"中文欄位名稱",
        "field_name_en":"英文欄位名稱",
        "ntu_yunlin":"台大雲林欄位名稱",
        "ntu_system":"台大體系醫整庫欄位名稱",
        "taiwan_cancer_registry":"台灣癌症登記中心",
        "AI_module":"雲醫癌AI模組"}.get(scheme, scheme)

    try:
        wb = load_workbook(cleaned_file)
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        output_cols = []
        mapped_orig_indices = set()

        # 自動加入匹配到的欄位
        for i, header in enumerate(headers):
            if header in alias_to_target:
                idx = i + 1
                target_name = alias_to_target[header]
                output_cols.append((idx, target_name))
                mapped_orig_indices.add(idx)

        # 加入動勾選的未匹配欄位
        for field in selected_fields:
            try:
                orig_idx = headers.index(field) + 1
                if orig_idx not in mapped_orig_indices:
                    output_cols.append((orig_idx, field))
            except ValueError:
                continue

        err_col_name = '錯誤註記說明(A:遺漏值 B:格式不符 C:邏輯錯誤 D:完全正確)'
        if err_col_name in headers:
            err_idx = headers.index(err_col_name) + 1
            if not any(col[0] == err_idx for col in output_cols):
                output_cols.append((err_idx, err_col_name))


        new_wb = Workbook()
        new_ws = new_wb.active
        for r_idx, row in enumerate(ws.iter_rows(), start=1):
            for c_idx, (orig_col_idx, target_name) in enumerate(output_cols, start=1):
                source_cell = ws.cell(row=r_idx, column=orig_col_idx)
                target_cell = new_ws.cell(row=r_idx, column=c_idx)
                
                if r_idx == 1:
                    target_cell.value = target_name
                    if source_cell.has_style:
                        target_cell.font = copy(source_cell.font)
                        target_cell.fill = copy(source_cell.fill)
                        target_cell.alignment = copy(source_cell.alignment)
                else:
                    copy_cell(source_cell, target_cell)

        for c_idx, (orig_col_idx, _) in enumerate(output_cols, start=1):
            new_ws.column_dimensions[get_column_letter(c_idx)].width = \
                ws.column_dimensions[get_column_letter(orig_col_idx)].width

        export_filename = f"fmt{fmt_name}_{base_name}_{scheme_display}.xlsx"
        temp_out = os.path.join(project_path, export_filename)
        new_wb.save(temp_out)
        resp = send_file(os.path.abspath(temp_out), as_attachment=True, download_name=export_filename)
        resp.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return resp

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@clean_bp.route("/api/preview", methods=["POST"])
@login_required
def api_preview():
    data = request.json
    job_id = data.get("job_id")
    scheme = data.get("scheme")
    selected_fields = data.get("fields", [])

    if not job_id:
        return jsonify({"ok": False, "error": "缺少 JobID"}), 400

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT Job.Path, Job.FileName, DataFormat.FmtName 
        FROM [Job] 
        JOIN [DataFormat] ON Job.FmtID = DataFormat.FmtID 
        WHERE Job.JobID=?
    """, (job_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"ok": False, "error": "找不到該紀錄"}), 404

    project_path, original_filename, fmt_name = row
    base_name, _ = os.path.splitext(original_filename)
    cleaned_file = os.path.join(project_path, f"fmt{fmt_name}_{base_name}_Clean.xlsx")

    if not os.path.exists(cleaned_file):
        return jsonify({"ok": False, "error": "清洗檔案不存在"}), 404

    # 取得欄位對照表
    alias_to_target = get_field_map(scheme, fmt_name)

    try:
        wb = load_workbook(cleaned_file, data_only=True)
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        
        # 決定輸出欄位
        output_cols = [(i+1, alias_to_target[h]) for i, h in enumerate(headers) if h in alias_to_target]
        mapped_indices = {c[0] for c in output_cols}
        
        # 加入使用者勾選的未匹配欄位 與 強制保留的錯誤註記
        for f in selected_fields + ['錯誤註記說明(A:遺漏值 B:格式不符 C:邏輯錯誤 D:完全正確)']:
            if f in headers:
                idx = headers.index(f) + 1
                if idx not in mapped_indices:
                    output_cols.append((idx, f))
                    mapped_indices.add(idx)

        # 讀取前 5 筆資料
        preview_data = []
        preview_headers = [col[1] for col in output_cols]
        
        for row in ws.iter_rows(min_row=2, max_row=6):
            row_data = [str(ws.cell(row=row[0].row, column=c_idx).value or "") for c_idx, _ in output_cols]
            preview_data.append(row_data)

        return jsonify({
            "ok": True,
            "headers": preview_headers,
            "data": preview_data
        })

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

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
    base_name = os.path.splitext(filename)[0]
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

            temp_xlsx = f"{project_folder}/{base_name}.xlsx"
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

    out_path, rep_path = f"{project_folder}/fmt{fmt_name}_{base_name}_Clean.xlsx", f"{project_folder}/fmt{fmt_name}_{base_name}_Report.xlsx"
    
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
    
    # 偵測資料體系
    detected_system, _ = detect_system(sorted_df.columns)

    return jsonify({
        "ok": True, 
        "project_id": JobID,
        "detected_system": detected_system,
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
            target_filename = f"fmt{fmt_name}_{base_name}_Clean.xlsx"
        elif file_type == "report":
            target_filename = f"fmt{fmt_name}_{base_name}_Report.xlsx"
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