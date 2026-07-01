import os
import re
from flask import Blueprint, request, jsonify, session, send_file
from modules.blueprint.data_gen import analyze_file_logic, process_file_logic

data_gen_bp = Blueprint('data_gen', __name__)
@data_gen_bp.route('/api/data_gen/analyze', methods=['POST'])
def analyze_file():
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "無檔案"}), 400
    file = request.files['file']
    
    raw_filename = file.filename or ""
    basename = os.path.basename(raw_filename)
    filename = re.sub(r'[\\/:*?"<>|\s]', '_', basename)
    if not filename.strip():
        filename = "uploaded_file"
        
    upload_folder = 'data/temp'
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    res, status = analyze_file_logic(file_path, filename)
    
    if res.get("ok"):
        session['last_gen_file'] = file_path
    return jsonify(res), status

@data_gen_bp.route('/api/data_gen/process', methods=['POST'])
def process_file():
    data = request.json
    format_id = data.get('format_id')
    selected_date_cols_raw = data.get('date_cols', [])
    extra_cols = data.get('extra_cols', []) 
    special_configs = data.get('special_configs', {}) 
    naming_scheme = data.get('naming_scheme', 'field_name_zh')
    
    file_path = session.get('last_gen_file')
    res, status = process_file_logic(file_path, format_id, selected_date_cols_raw, extra_cols, special_configs, naming_scheme)
    if res.get("ok") and "out_path" in res:
        session['last_gen_output'] = res.pop("out_path")
    return jsonify(res), status

@data_gen_bp.route('/api/data_gen/download')
def download_file():
    path = session.get('last_gen_output')
    if path and os.path.exists(path):
        return send_file(os.path.abspath(path), as_attachment=True)
    return "檔案不存在", 404