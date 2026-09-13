import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from uuid import uuid4
from flask import Blueprint, request, jsonify, session, send_file
from modules.blueprint.data_gen import analyze_file_logic, process_file_logic
from modules.services.auth import login_required
from modules.services.db import get_conn
from flask import render_template

data_gen_bp = Blueprint('data_gen', __name__, template_folder='../blueprint/data_gen/templates')
DATA_GEN_UPLOAD_ROOT = Path(tempfile.gettempdir()) / "CancerRegistry_System" / "data_gen"
DATA_GEN_MAX_AGE_SECONDS = 3600

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

def _clear_generation_session(remove_files=False):
    upload_folder = session.get('last_gen_folder')
    session.pop('last_gen_file', None)
    session.pop('last_gen_output', None)
    session.pop('last_gen_folder', None)
    if remove_files and upload_folder:
        _remove_upload_folder(upload_folder)

def _cleanup_expired_uploads():
    if not DATA_GEN_UPLOAD_ROOT.exists():
        return
    expiry = time.time() - DATA_GEN_MAX_AGE_SECONDS
    for user_folder in DATA_GEN_UPLOAD_ROOT.iterdir():
        if not user_folder.is_dir():
            continue
        for upload_folder in user_folder.iterdir():
            if upload_folder.is_dir() and upload_folder.stat().st_mtime < expiry:
                _remove_upload_folder(upload_folder)

def _session_file_path(key):
    path = session.get(key)
    upload_folder = session.get('last_gen_folder')
    if not path or not upload_folder:
        return None
    try:
        resolved_path = Path(path).resolve()
        resolved_folder = Path(upload_folder).resolve()
        resolved_path.relative_to(resolved_folder)
        return resolved_path
    except (OSError, ValueError):
        return None

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
        
    _cleanup_expired_uploads()
    _clear_generation_session(remove_files=True)
    file_path = _create_upload_path(session.get('id'), filename)
    file.save(file_path)
    
    res, status = analyze_file_logic(file_path, filename)
    
    if res.get("ok"):
        session['last_gen_folder'] = str(file_path.parent)
        session['last_gen_file'] = str(file_path)
    else:
        _remove_upload_folder(file_path.parent)
    return jsonify(res), status

@data_gen_bp.route('/api/data_gen/process', methods=['POST'])
@login_required
def process_file():
    data = request.json
    format_id = data.get('format_id')
    selected_date_cols_raw = data.get('date_cols', [])
    extra_cols = data.get('extra_cols', []) 
    special_configs = data.get('special_configs', {}) 
    naming_scheme = data.get('naming_scheme', 'field_name_zh')
    
    file_path = _session_file_path('last_gen_file')
    res, status = process_file_logic(file_path, format_id, selected_date_cols_raw, extra_cols, special_configs, naming_scheme)
    if res.get("ok") and "out_path" in res:
        session['last_gen_output'] = res.pop("out_path")
        if file_path:
            file_path.unlink(missing_ok=True)
            session.pop('last_gen_file', None)
    return jsonify(res), status

@data_gen_bp.route('/api/data_gen/download')
@login_required
def download_file():
    path = _session_file_path('last_gen_output')
    if path and os.path.exists(path):
        response = send_file(os.path.abspath(path), as_attachment=True)
        upload_folder = path.parent
        _clear_generation_session()
        response.call_on_close(lambda: _remove_upload_folder(upload_folder))
        return response
    return "檔案不存在", 404