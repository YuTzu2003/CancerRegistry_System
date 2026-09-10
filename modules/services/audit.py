import json
import logging
import traceback
from flask import g, has_request_context, request, session
from modules.services.db import get_conn

def write_audit_log(action, detail=None, user_id=None, remote_addr=None):
    if user_id is None and has_request_context():
        user_id = session.get("id")
    if remote_addr is None and has_request_context():
        remote_addr = request.remote_addr

    try:
        detail_json = json.dumps(detail or {}, ensure_ascii=False, default=str)
        conn = get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO dbo.Audit_logs ([Action], [CreatedAt], [User_id], [detail_json], [Remote_addr]) VALUES (?, SYSDATETIMEOFFSET(), ?, ?, ?)",(action, user_id, detail_json, remote_addr),)
            conn.commit()
            if has_request_context():
                g.audit_written = True
        finally:
            conn.close()
    except Exception:
        logging.exception("Unable to write audit log for action %s", action)


def register_audit_logging(app):
    @app.after_request
    def record_request(response):
        if (
            request.endpoint == "static"
            or request.endpoint == "health_check"
            or not session.get("id")
            or getattr(g, "audit_written", False)
        ):
            return response
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"} or response.status_code >= 500:
            return response

        blueprint = request.blueprint or "system"
        endpoint = (request.endpoint or "unknown").rsplit(".", 1)[-1]
        write_audit_log(f"{blueprint}_{endpoint}_{request.method.lower()}",{"status_code": response.status_code},)
        return response

    @app.teardown_request
    def record_exception(error):
        if error is None:
            return
        blueprint = request.blueprint or "system"
        endpoint = (request.endpoint or "unknown").rsplit(".", 1)[-1]
        write_audit_log(
            f"{blueprint}_{endpoint}_error",
            {
                "status": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": "".join(traceback.format_exception(type(error), error, error.__traceback__)),
            },
        )

