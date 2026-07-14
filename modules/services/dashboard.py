from flask import Blueprint, request, session, jsonify
from modules.services.auth import login_required
from modules.blueprint.dashboard import load_user_favorites, save_user_favorites
from modules.blueprint.dashboard.reply import get_chart_insight_logic
from flask import send_file
from modules.blueprint.dashboard.export_report import generate_export_files
import os
import re
import logging
import datetime
import pandas as pd
from flask import render_template

dashboard_bp = Blueprint('dashboard', __name__, template_folder='../blueprint/dashboard/templates')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DASHBOARD_DATA = os.path.join(BASE_DIR, 'tasks', 'data')
os.makedirs(DASHBOARD_DATA, exist_ok=True)

@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    uploaded_files = []
    if os.path.isdir(DASHBOARD_DATA):
        for fname in os.listdir(DASHBOARD_DATA):
            if fname.lower().endswith((".xls", ".xlsx")):
                fpath = os.path.join(DASHBOARD_DATA, fname)
                mtime = os.path.getmtime(fpath)
                uploaded_files.append({"name": fname,"time": datetime.datetime.fromtimestamp(mtime).strftime("%Y/%m/%d %H:%M")})
        uploaded_files.sort(key=lambda x: x["time"],reverse=True)
    return render_template("dashboard.html", active="dashboard",uploaded_files=uploaded_files)

@dashboard_bp.route("/dashboard/upload", methods=["POST"])
@login_required
def dashboard_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "未選擇檔案"}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ("xls", "xlsx"):
        return jsonify({"ok": False, "error": "僅接受 .xls 或 .xlsx 格式"}), 400
    raw_filename = f.filename or ""
    basename = os.path.basename(raw_filename)
    filename = re.sub(r'[\\/:*?"<>|\s]', '_', basename)
    if not filename.strip() or filename == f".{ext}":
        filename = f"uploaded_file.{ext}"
    save_path = os.path.join(DASHBOARD_DATA, filename)
    f.save(save_path)
    logging.info(f"Dashboard upload: {filename} saved to {save_path}")
    return jsonify({"ok": True, "filename": filename})


@dashboard_bp.route('/api/dashboard/year_range', methods=['POST'])
@login_required
def dashboard_year_range():
    data = request.json or {}
    filename = os.path.basename(data.get("filename", ""))
    if not filename:
        return jsonify({"ok": False, "error": "未選擇檔案"}), 400

    fpath = os.path.join(DASHBOARD_DATA, filename)
    if not os.path.isfile(fpath):
        return jsonify({"ok": False, "error": "檔案不存在"}), 404

    try:
        from modules.blueprint.dashboard.chart_analytics import get_column_names
        df = pd.read_excel(fpath)
        cols = get_column_names(df)
        year_col = cols.get("year_col")
        if not year_col or year_col not in df.columns:
            return jsonify({"ok": False, "error": "找不到診斷年度欄位"}), 400

        years = pd.to_numeric(df[year_col].astype(str).str[:4], errors="coerce").dropna()
        if years.empty:
            return jsonify({"ok": False, "error": "查無符合條件資料！"}), 400

        return jsonify({
            "ok": True,
            "year_start": int(years.min()),
            "year_end": int(years.max())
        }), 200
    except Exception as e:
        logging.error(f"Error reading dashboard year range: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@dashboard_bp.route("/dashboard/delete", methods=["POST"])
@login_required
def dashboard_delete():
    data = request.json or {}
    filename = data.get("filename", "")
    if not filename:
        return jsonify({"ok": False, "error": "未指定檔案名稱"}), 400
    fpath = os.path.join(DASHBOARD_DATA, filename)
    if not os.path.isfile(fpath):
        return jsonify({"ok": False, "error": "檔案不存在"}), 404
    os.remove(fpath)
    logging.info(f"Dashboard delete: {filename}")
    return jsonify({"ok": True})

@dashboard_bp.route("/api/chart_insight", methods=["POST"])
@login_required
def chart_insight_route():
    try:
        data = request.json or {}
        result = get_chart_insight_logic(data)
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error in chart_insight_route: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@dashboard_bp.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    db_id = session.get("id")
    user_favs = load_user_favorites(db_id)
    return jsonify({"ok": True, "favorites": user_favs}), 200

@dashboard_bp.route('/api/favorites', methods=['POST'])
@login_required
def add_favorite():
    db_id = session.get("id")
    data = request.json or {}
    name = data.get("name", "").strip()
    behavior = data.get("behavior", "")
    cancers = data.get("cancers", [])
    main_category = data.get("main_category", "")
    sub_category = data.get("sub_category", "")
    user_favs = load_user_favorites(db_id)
    
    if any(f.get("name") == name for f in user_favs):
        return jsonify({"ok": False, "error": "已有相同的最愛範本名稱"}), 400
        
    max_id = max([f.get("id", 0) for f in user_favs], default=0)
    new_id = max_id + 1
    new_fav = {"id": new_id,"name": name,"behavior": behavior,"cancers": cancers, "main_category": main_category, "sub_category": sub_category}
    user_favs.append(new_fav)
    save_user_favorites(db_id, user_favs)
    return jsonify({"ok": True, "favorite": new_fav}), 200


@dashboard_bp.route('/api/favorites/<int:fav_id>', methods=['PUT'])
@login_required
def rename_favorite(fav_id):
    db_id = session.get("id")
    data = request.json or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "error": "請輸入新範本名稱"}), 400
     
    user_favs = load_user_favorites(db_id)
    if any(f.get("name") == name and f.get("id") != fav_id for f in user_favs):
        return jsonify({"ok": False, "error": "已有相同的最愛範本名稱"}), 400
       
    for f in user_favs:
        if f.get("id") == fav_id:
            f["name"] = name
            break     
    save_user_favorites(db_id, user_favs)
    return jsonify({"ok": True}), 200

@dashboard_bp.route('/api/favorites/<int:fav_id>', methods=['DELETE'])
@login_required
def delete_favorite(fav_id):
    db_id = session.get("id")
    user_favs = load_user_favorites(db_id)
    new_user_favs = [f for f in user_favs if f.get("id") != fav_id]
    if len(new_user_favs) == len(user_favs):
        return jsonify({"ok": False, "error": "找不到該最愛範本"}), 404      
    save_user_favorites(db_id, new_user_favs)
    return jsonify({"ok": True}), 200

@dashboard_bp.route('/api/dashboard/analyze_file', methods=['POST'])
@login_required
def analyze_dashboard_file_route():
    data = request.json or {}
    filename = data.get("filename", "")
    cancers = data.get("cancers", [])
    year_start = data.get("year_start", "")
    year_end = data.get("year_end", "")
    behavior = data.get("behavior", "")
    
    if not filename:
        return jsonify({"ok": False, "error": "未提供檔案名稱"}), 400
        
    try:
        from modules.blueprint.dashboard.chart_analytics import analyze_dashboard_file
        chart_data = analyze_dashboard_file(filename, cancers, year_start, year_end, behavior)
        return jsonify({"ok": True, "data": chart_data}), 200
    except Exception as e:
        import logging
        logging.error(f"Error analyzing dashboard file: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500



@dashboard_bp.route('/dashboard/export_report', methods=['GET'])
@login_required
def export_report_page():
    return render_template('export_report.html', active='dashboard')

@dashboard_bp.route('/api/dashboard/export', methods=['POST'])
@login_required
def export_report_api():
    data = request.json or {}
    format_pdf = data.get('format_pdf', True)
    format_word = data.get('format_word', False)
    charts = data.get('charts', [])
    
    if not charts:
        return jsonify({'ok': False, 'error': '沒有圖表資料可匯出'}), 400
        
    output_dir = os.path.join(DASHBOARD_DATA, 'exports')
    
    try:
        file_obj, mimetype, dl_name = generate_export_files(format_pdf, format_word, charts, output_dir)
        if file_obj:
            return send_file(file_obj, mimetype=mimetype, as_attachment=True, download_name=dl_name)
        else:
            return jsonify({'ok': False, 'error': '無法產生匯出檔案'}), 500
    except Exception as e:
        import logging
        logging.error(f'Export error: {e}')
        return jsonify({'ok': False, 'error': str(e)}), 500