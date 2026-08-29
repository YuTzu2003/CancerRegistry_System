from flask import Flask,render_template,session,request,jsonify,flash
import os
import logging
import sys
from dotenv import load_dotenv
from modules.services import auth_bp, login_required, history_bp, clean_bp, data_gen_bp, dashboard_bp, histology_mapping_bp
from modules.services.db import get_conn
import modules.blueprint.dashboard.national_import
from modules.blueprint.admin.member import member_bp
from modules.blueprint.auth.key_application import key_application_bp
import modules.blueprint.auth.key_access
from modules.blueprint.admin.key_approval import key_approval_bp
import jinja2

load_dotenv()

logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(message)s',datefmt='%Y-%m-%d %H:%M:%S',handlers=[logging.StreamHandler(sys.stdout)])
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.handlers = []
werkzeug_logger.propagate = True

app = Flask(__name__)
app.jinja_loader = jinja2.ChoiceLoader([jinja2.FileSystemLoader('modules/blueprint/templates'),jinja2.FileSystemLoader('templates')])
app.secret_key = "your_secret_key"
app.register_blueprint(auth_bp)
app.register_blueprint(member_bp)
app.register_blueprint(history_bp)
app.register_blueprint(clean_bp)
app.register_blueprint(data_gen_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(histology_mapping_bp)
app.register_blueprint(key_application_bp)
app.register_blueprint(key_approval_bp)

BASE_DIR = os.path.dirname(__file__)
Jobs_FOLDER = 'tasks/Jobs'
DASHBOARD_DATA = os.path.join(BASE_DIR, 'tasks', 'data')
os.makedirs(Jobs_FOLDER, exist_ok=True)
os.makedirs(DASHBOARD_DATA, exist_ok=True)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"csv","xls","xlsx","txt"}

@app.context_processor
def inject_nav():
    NAV_ITEMS = [
        {"title":"資料審核", "icon":"bi-funnel", "subitems": [
            {"endpoint":"clean.clean","title":"資料清洗","icon":"bi-play-circle"},
            {"endpoint":"history.history","title":"資料審核紀錄","icon":"bi-file-earmark-text"}
        ]},
        {"endpoint":"data_gen.dataGen","title":"虛擬資料生成","icon":"bi-database-add"},
        {"endpoint":"key_application.application","title":"權限申請","icon":"bi-key"},
        {"title":"報表分析","icon":"bi-bar-chart", "subitems": [
            {"endpoint":"dashboard.dashboard","title":"年報分析","icon":"bi-bar-chart"},
            {"endpoint":"dashboard.compare","title":"年度比較","icon":"bi-columns-gap"},
            {"endpoint":"auth.data_update_access","title":"資料維護","icon":"bi-database-gear"}
        ]},
    ]
    if session.get("position") == "Admin":
        # NAV_ITEMS.append({"endpoint":"rag_config", "title": "RAG知識庫", "icon": "bi-robot"})
        NAV_ITEMS.append({"title":"權限管理", "icon":"bi-shield-lock", "subitems": [
            {"endpoint":"member.member", "title":"使用者管理", "icon":"bi-people"},
            {"endpoint":"key_approval.key_approval", "title":"金鑰申請審核", "icon":"bi-key-fill"},
        ]})
        
    provider = os.environ.get("LLM_PROVIDER")
    if provider and provider.lower() == "openai":
        model = os.environ.get("OPENAI_MODEL")
    else:
        model = os.environ.get("LLM_MODEL")
        
    return {
        "nav_items": NAV_ITEMS,
        "llm_provider": provider or "ollama",
        "llm_model": model
    }

@app.route("/")
@login_required
def index():
    pending_application_count = 0
    key_application_status = ""
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(TotalCount) as Sum_TotalCount ,avg(CompletenessScore) as Avg_CompletenessScore FROM [Hospital_data].[dbo].[Job];")
        row = cursor.fetchone()
        stats = {
            "sum_total_count": f"{int(getattr(row,'Sum_TotalCount',0) or 0):,}",
            "avg_completeness_score": f"{(getattr(row,'Avg_CompletenessScore',0) or 0)*100:.2f}%"
        }
        if session.get("position") == "Admin":
            cursor.execute("SELECT COUNT(*) AS PendingCount FROM dbo.User_applications WHERE Status = 'Pending'")
            pending_application_count = int(getattr(cursor.fetchone(), "PendingCount", 0) or 0)
        else:
            cursor.execute(
                "SELECT TOP 1 Status FROM dbo.User_applications WHERE UserID = ? ORDER BY CreatedAt DESC",
                session["userid"],
            )
            row = cursor.fetchone()
            key_application_status = row[0] if row and row[0] in {"Approved", "Rejected"} else ""
        conn.close()
    except Exception as e:
        app.logger.error(f"Error fetching dashboard stats: {e}")
        stats = {"sum_total_count": "0", "avg_completeness_score": "0.0%"}
    
    return render_template(
        "index.html",
        active="index",
        stats=stats,
        pending_application_count=pending_application_count,
        key_application_status=key_application_status,
    )





# @app.route("/rag_config")
# @admin_required
# def rag_config(): return render_template("rag_config.html", active="rag_config")

if __name__ == "__main__":
    flask_port = int(os.environ.get("FLASK_PORT"))
    app.run(host="0.0.0.0", port=flask_port, debug=True)
