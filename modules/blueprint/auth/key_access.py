import secrets
import re
from functools import wraps

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from modules.services.auth import auth_bp, login_required
from modules.services.db import get_conn


DATA_UPDATE_ACCESS_TOKEN = "data_update_access_token"
DATA_UPDATE_ACCESS_USER = "data_update_access_user"


def has_data_update_access():
    return session.get("position") == "Admin" or (
        bool(session.get(DATA_UPDATE_ACCESS_TOKEN))
        and session.get(DATA_UPDATE_ACCESS_USER) == session.get("userid")
    )


def clear_data_update_access():
    session.pop(DATA_UPDATE_ACCESS_TOKEN, None)
    session.pop(DATA_UPDATE_ACCESS_USER, None)


def _indicator_destination(values):
    """Only allow the indicator-maintenance destination and safe page parameters."""
    if values.get('next') != 'indicator_definitions':
        return {}
    result = {'next': 'indicator_definitions'}
    cancer = str(values.get('cancer') or '')
    version = str(values.get('version') or '')
    if re.fullmatch(r'[A-Za-z0-9_]{1,50}', cancer):
        result['cancer'] = cancer
    if version == 'default' or re.fullmatch(r'[0-9]{1,10}', version):
        result['version'] = version
    return result


def _maintenance_destination(context):
    if context.get('next') == 'indicator_definitions':
        return url_for('indicators.indicator_definitions_page', **{key: value for key, value in context.items() if key != 'next'})
    return url_for('auth.data_management')


def data_update_key_required(view=None, *, destination=None):
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            if not has_data_update_access():
                if destination == 'indicator_definitions' and request.path.startswith('/api/'):
                    return jsonify({'ok': False, 'error': '請先完成資料維護 Key 驗證。'}), 403
                flash("請先輸入有效且已啟用的 Key，才能維護資料。", "danger")
                context = _indicator_destination({**request.args, 'next': destination}) if destination else {}
                return redirect(url_for("auth.data_update_access", **context))
            return func(*args, **kwargs)
        return decorated_function
    return decorator(view) if view is not None else decorator


@auth_bp.route("/dashboard/data-update")
@login_required
def data_update_access():
    context = _indicator_destination(request.args)
    if has_data_update_access():
        return redirect(_maintenance_destination(context))
    clear_data_update_access()
    active = 'indicators.indicator_definitions_page' if context else 'data_update_access'
    return render_template("key_access.html", active=active, access_destination=context)


@auth_bp.route("/dashboard/data-update/select")
@login_required
@data_update_key_required
def data_management():
    return render_template("data_management.html", active="data_update_access")


@auth_bp.route("/dashboard/data-update/access", methods=["POST"])
@login_required
def verify_data_update_access():
    context = _indicator_destination(request.form)
    api_key = request.form.get("api_key", "").strip()
    if not api_key:
        flash("請輸入金鑰。", "danger")
        return redirect(url_for("auth.data_update_access", **context))

    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 1 FROM dbo.User_applications "
            "WHERE UserID = ? AND API_key = ? AND Status = 'Active' AND End_time >= GETDATE()",
            session["userid"], api_key,
        )
        key_is_valid = cursor.fetchone() is not None
    finally:
        conn.close()

    if not key_is_valid:
        flash("金鑰失效、未啟用或帳號不符，請確認金鑰與登入帳號。", "danger")
        return redirect(url_for("auth.data_update_access", **context))

    session[DATA_UPDATE_ACCESS_TOKEN] = secrets.token_urlsafe(24)
    session[DATA_UPDATE_ACCESS_USER] = session["userid"]
    return redirect(_maintenance_destination(context))
