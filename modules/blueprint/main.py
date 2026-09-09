from flask import jsonify, render_template, session

from modules.services.db import get_conn
from modules.services.twcr_updates import fetch_twcr_updates


def register_main_routes(app, app_env, login_required):
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "environment": app_env})

    @app.route("/")
    @login_required
    def index():
        pending_application_count = 0
        key_application_status = ""
        announcements = []
        try:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT SUM(TotalCount) as Sum_TotalCount ,avg(CompletenessScore) as Avg_CompletenessScore FROM [Job];")
            row = cursor.fetchone()
            stats = {
                "sum_total_count": f"{int(getattr(row,'Sum_TotalCount',0) or 0):,}",
                "avg_completeness_score": f"{(getattr(row,'Avg_CompletenessScore',0) or 0)*100:.2f}%"
            }
            announcements = fetch_twcr_updates()
            if session.get("position") == "Admin":
                cursor.execute("SELECT COUNT(*) AS PendingCount FROM dbo.User_applications WHERE Status = 'Pending'")
                pending_application_count = int(getattr(cursor.fetchone(), "PendingCount", 0) or 0)
            else:
                cursor.execute("SELECT TOP 1 Status FROM dbo.User_applications WHERE UserID = ? ORDER BY CreatedAt DESC",session["userid"],)
                row = cursor.fetchone()
                key_application_status = row[0] if row and row[0] in {"Approved", "Rejected"} else ""
            conn.close()
        except Exception as e:
            app.logger.error(f"Error fetching dashboard stats: {e}")
            stats = {"sum_total_count": "0", "avg_completeness_score": "0.0%"}

        return render_template("index.html",active="index",stats=stats,pending_application_count=pending_application_count,key_application_status=key_application_status,announcements=announcements,)
