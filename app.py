from flask import Flask,render_template,session
import os
import logging
import sys
from services.auth import auth_bp, login_required, admin_required
from services.member import member_bp
from services.history import history_bp
from services.clean import clean_bp
from services.data_gen import data_gen_bp
from modules.db import get_conn

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
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

BASE_DIR = os.path.dirname(__file__)
Jobs_FOLDER = 'static/Jobs'
os.makedirs(Jobs_FOLDER, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"csv","xls","xlsx","txt"}

@app.context_processor
def inject_nav():
    NAV_ITEMS = [
        {"endpoint":"clean.clean","title":"資料清洗模組","icon":"bi-funnel"},
        {"endpoint":"history.history","title":"資料審核紀錄","icon":"bi-file-earmark-text"},
        {"endpoint":"dataGen","title":"虛擬資料生成","icon":"bi-database-add"},
        {"endpoint":"analytics","title":"統計分析","icon":"bi-bar-chart"},
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

# ---- other ------------------------------------------
@app.route("/dataGen")
@login_required
def dataGen(): return render_template("dataGen.html", active="dataGen")

@app.route("/analytics")
@login_required
def analytics(): return render_template("analytics.html", active="analytics")

# @app.route("/rag_config")
# @admin_required
# def rag_config(): return render_template("rag_config.html", active="rag_config")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)