from flask import Flask,render_template,session,request,jsonify,flash
import os
import logging
import sys
from dotenv import load_dotenv
import datetime
from modules.services import auth_bp, login_required, member_bp, history_bp, clean_bp, data_gen_bp, dashboard_bp
from modules.services.db import get_conn

load_dotenv()

logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(message)s',datefmt='%Y-%m-%d %H:%M:%S',handlers=[logging.StreamHandler(sys.stdout)])
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.handlers = []
werkzeug_logger.propagate = True

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.register_blueprint(auth_bp)
app.register_blueprint(member_bp)
app.register_blueprint(history_bp)
app.register_blueprint(clean_bp)
app.register_blueprint(data_gen_bp)
app.register_blueprint(dashboard_bp)

BASE_DIR = os.path.dirname(__file__)
Jobs_FOLDER = 'work/Jobs'
DASHBOARD_DATA = os.path.join(BASE_DIR, 'work', 'data')
os.makedirs(Jobs_FOLDER, exist_ok=True)
os.makedirs(DASHBOARD_DATA, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"csv","xls","xlsx","txt"}

@app.context_processor
def inject_nav():
    NAV_ITEMS = [
        {"endpoint":"clean.clean","title":"資料清洗模組","icon":"bi-funnel"},
        {"endpoint":"history.history","title":"資料審核紀錄","icon":"bi-file-earmark-text"},
        {"endpoint":"dataGen","title":"虛擬資料生成","icon":"bi-database-add"},
        {"endpoint":"dashboard","title":"年報分析","icon":"bi-bar-chart"},
    ]
    if session.get("position") == "Admin":
        # NAV_ITEMS.append({"endpoint":"rag_config", "title": "RAG知識庫", "icon": "bi-robot"})
        NAV_ITEMS.append({"endpoint":"member.member", "title": "使用者管理", "icon": "bi-people"})
    return {"nav_items": NAV_ITEMS}

@app.route("/")
@login_required
def index():
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(TotalCount) as Sum_TotalCount ,avg(CompletenessScore) as Avg_CompletenessScore FROM [Hospital_data].[dbo].[Job];")
        row = cursor.fetchone()
        stats = {
            "sum_total_count": f"{int(getattr(row,'Sum_TotalCount',0) or 0):,}",
            "avg_completeness_score": f"{(getattr(row,'Avg_CompletenessScore',0) or 0)*100:.2f}%"
        }
        conn.close()
    except Exception as e:
        app.logger.error(f"Error fetching dashboard stats: {e}")
        stats = {"sum_total_count": "0", "avg_completeness_score": "0.0%"}
    
    return render_template("index.html", active="index", stats=stats)

@app.route("/dataGen")
@login_required
def dataGen():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT FmtID, FmtName, Version FROM [Hospital_data].[dbo].[DataFormat] ORDER BY FmtName ASC")
    rows = cursor.fetchall()
    formats = [{"id": str(r[0]), "name": str(r[1]), "version": str(r[2])} for r in rows]
    conn.close()
    return render_template("dataGen.html", active="dataGen", formats=formats)


def _list_dashboard_files():
    files = []
    if os.path.isdir(DASHBOARD_DATA):
        for fname in os.listdir(DASHBOARD_DATA):
            if fname.lower().endswith(('.xls', '.xlsx')):
                fpath = os.path.join(DASHBOARD_DATA, fname)
                mtime = os.path.getmtime(fpath)
                files.append({
                    "name": fname,
                    "time": datetime.datetime.fromtimestamp(mtime).strftime("%Y/%m/%d %H:%M"),
                })
        files.sort(key=lambda x: x["time"], reverse=True)
    return files


@app.route("/dashboard")
@login_required
def dashboard():
    uploaded_files = _list_dashboard_files()
    return render_template("dashboard.html", active="dashboard", uploaded_files=uploaded_files)


@app.route("/dashboard/upload", methods=["POST"])
@login_required
def dashboard_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"ok": False, "error": "未選擇檔案"}), 400
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in ("xls", "xlsx"):
        return jsonify({"ok": False, "error": "僅接受 .xls 或 .xlsx 格式"}), 400
    import re
    raw_filename = f.filename or ""
    basename = os.path.basename(raw_filename)
    filename = re.sub(r'[\\/:*?"<>|\s]', '_', basename)
    if not filename.strip() or filename == f".{ext}":
        filename = f"uploaded_file.{ext}"
    save_path = os.path.join(DASHBOARD_DATA, filename)
    f.save(save_path)
    logging.info(f"Dashboard upload: {filename} saved to {save_path}")
    return jsonify({"ok": True, "filename": filename})


@app.route("/dashboard/delete", methods=["POST"])
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


# @app.route("/rag_config")
# @admin_required
# def rag_config(): return render_template("rag_config.html", active="rag_config")

if __name__ == "__main__":
    flask_port = int(os.environ.get("FLASK_PORT"))
    app.run(host="0.0.0.0", port=flask_port, debug=True)