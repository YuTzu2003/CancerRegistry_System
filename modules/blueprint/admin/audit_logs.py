import json
from flask import Blueprint, render_template, request
from modules.services.auth import admin_required, login_required
from modules.services.db import get_conn

audit_logs_bp = Blueprint("audit_logs", __name__, template_folder="templates")
ORDER_COLUMNS = {"created_at": "CreatedAt","user_id": "User_id","action": "Action",}

@audit_logs_bp.route("/admin/audit-logs")
@login_required
@admin_required
def audit_logs():
    filters = {
        "q": request.args.get("q", "").strip(),
        "action": request.args.get("action", "").strip(),
        "start": request.args.get("start", "").strip(),
        "end": request.args.get("end", "").strip(),
        "sort": request.args.get("sort", "created_at"),
        "order": request.args.get("order", "desc"),
    }
    order_column = ORDER_COLUMNS.get(filters["sort"], "CreatedAt")
    order_direction = "ASC" if filters["order"] == "asc" else "DESC"

    conditions = []
    parameters = []
    if filters["q"]:
        conditions.append("(u.[Name] LIKE ? OR a.[User_id] LIKE ? OR a.[Action] LIKE ? OR a.[detail_json] LIKE ?)")
        keyword = f"%{filters['q']}%"
        parameters.extend((keyword, keyword, keyword, keyword))
    if filters["action"]:
        conditions.append("a.[Action] = ?")
        parameters.append(filters["action"])
    if filters["start"]:
        conditions.append("a.[CreatedAt] >= ?")
        parameters.append(filters["start"])
    if filters["end"]:
        conditions.append("a.[CreatedAt] < DATEADD(day, 1, CAST(? AS date))")
        parameters.append(filters["end"])

    where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT [Action] FROM dbo.Audit_logs ORDER BY [Action]")
    actions = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT a.[LogID], a.[Action], a.[CreatedAt], a.[User_id], a.[detail_json], a.[Remote_addr], COALESCE(NULLIF(u.[Name], ''), a.[User_id]) AS UserName FROM dbo.Audit_logs AS a LEFT JOIN dbo.Users AS u ON a.[User_id] = u.UserID " + where_clause + f" ORDER BY a.[{order_column}] {order_direction}, a.[LogID] DESC OFFSET 0 ROWS FETCH NEXT 500 ROWS ONLY", parameters)
    columns = [column[0] for column in cursor.description]
    logs = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()

    for log in logs:
        try:
            log["detail"] = json.dumps(json.loads(log["detail_json"] or "{}"), ensure_ascii=False, indent=2)
        except (TypeError, json.JSONDecodeError):
            log["detail"] = log["detail_json"] or ""

    return render_template("audit_logs.html", active="audit_logs", logs=logs, actions=actions, filters=filters,)