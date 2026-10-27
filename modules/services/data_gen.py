import base64
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4
from flask import Blueprint, request, jsonify, session
from modules.blueprint.data_gen import analyze_file_logic, process_file_logic
from modules.services.auth import login_required
from modules.services.db import get_conn
from flask import render_template

data_gen_bp = Blueprint('data_gen', __name__, template_folder='../blueprint/data_gen/templates')
DATA_GEN_UPLOAD_ROOT = Path(tempfile.gettempdir()) / "CancerRegistry_System" / "data_gen"

def _create_upload_path(user_id, filename):
    safe_user_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(user_id))
    upload_folder = DATA_GEN_UPLOAD_ROOT / safe_user_id / uuid4().hex
    upload_folder.mkdir(parents=True, exist_ok=False)
    return upload_folder / filename

def _remove_upload_folder(upload_folder):
    try:
        resolved_folder = Path(upload_folder).resolve()
        resolved_folder.relative_to(DATA_GEN_UPLOAD_ROOT.resolve())
        shutil.rmtree(resolved_folder, ignore_errors=True)
    except (OSError, ValueError):
        return

@data_gen_bp.route("/dataGen")
@login_required
def dataGen():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT FmtID, FmtName, Version FROM [DataFormat] ORDER BY FmtName ASC")
    rows = cursor.fetchall()
    formats = [{"id": str(r[0]), "name": str(r[1]), "version": str(r[2])} for r in rows]
    conn.close()
    return render_template("dataGen.html", active="dataGen", formats=formats)
@data_gen_bp.route('/api/data_gen/analyze', methods=['POST'])
@login_required
def analyze_file():
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "無檔案"}), 400
    file = request.files['file']
    
    raw_filename = file.filename or ""
    basename = os.path.basename(raw_filename)
    filename = re.sub(r'[\\/:*?"<>|\s]', '_', basename)
    if not filename.strip():
        filename = "uploaded_file"
    extension = os.path.splitext(filename)[1].lower()
    if extension not in {".txt", ".csv", ".xls", ".xlsx"}:
        return jsonify({"ok": False, "error": "僅接受txt、csv、xls、xlsx 格式"}), 400
    format_id = request.form.get("format_id")
    txt_has_header = request.form.get("txt_has_header") == "true" if extension == ".txt" else None
        
    file_path = _create_upload_path(session.get('id'), filename)
    try:
        file.save(file_path)
        res, status = analyze_file_logic(
            file_path,
            filename,
            format_id=format_id,
            txt_has_header=txt_has_header,
        )
        return jsonify(res), status
    finally:
        _remove_upload_folder(file_path.parent)

@data_gen_bp.route('/api/data_gen/process', methods=['POST'])
@login_required
def process_file():
    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"ok": False, "error": "請重新上傳檔案"}), 400

    try:
        data = json.loads(request.form.get('options', '{}'))
    except json.JSONDecodeError:
        return jsonify({"ok": False, "error": "產生設定格式不正確"}), 400

    format_id = data.get('format_id')
    selected_date_cols_raw = data.get('date_cols', [])
    extra_cols = data.get('extra_cols', [])
    special_configs = data.get('special_configs', {})
    naming_scheme = data.get('naming_scheme', 'field_name_zh')
    txt_has_header = request.form.get('txt_has_header') == 'true'

    raw_filename = uploaded_file.filename or ''
    filename = re.sub(r'[\\/:*?"<>|\s]', '_', os.path.basename(raw_filename)) or 'uploaded_file'
    file_path = _create_upload_path(session.get('id'), filename)
    try:
        uploaded_file.save(file_path)
        res, status = process_file_logic(
            file_path,
            format_id,
            selected_date_cols_raw,
            extra_cols,
            special_configs,
            naming_scheme,
            txt_has_header=txt_has_header,
        )
        if res.get('ok') and 'out_path' in res:
            output_path = Path(res.pop('out_path'))
            res['download_filename'] = output_path.name
            res['download_data'] = base64.b64encode(output_path.read_bytes()).decode('ascii')
        return jsonify(res), status
    finally:
        # 分析與生成僅在單一請求中暫存，回應送出前即清除伺服器端檔案。
        _remove_upload_folder(file_path.parent)
