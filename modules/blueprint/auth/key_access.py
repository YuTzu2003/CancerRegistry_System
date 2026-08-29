import secrets
from functools import wraps

from flask import flash, redirect, render_template, request, session, url_for

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


def data_update_key_required(view):
    @wraps(view)
    def decorated_function(*args, **kwargs):
        if not has_data_update_access():
            flash("請先輸入有效且已啟用的 Key，才能維護資料。", "danger")
            return redirect(url_for("auth.data_update_access"))
        return view(*args, **kwargs)

    return decorated_function


@auth_bp.route("/dashboard/data-update")
@login_required
def data_update_access():
    if has_data_update_access():
        return redirect(url_for("auth.data_update_selection"))
    clear_data_update_access()
    return render_template("key_access.html", active="data_update_access")


@auth_bp.route("/dashboard/data-update/select")
@login_required
@data_update_key_required
def data_update_selection():
    return render_template("data_update_selection.html", active="data_update_access")


@auth_bp.route("/dashboard/data-update/access", methods=["POST"])
@login_required
def verify_data_update_access():
    api_key = request.form.get("api_key", "").strip()
    if not api_key:
        flash("請輸入金鑰。", "danger")
        return redirect(url_for("auth.data_update_access"))

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
        return redirect(url_for("auth.data_update_access"))

    session[DATA_UPDATE_ACCESS_TOKEN] = secrets.token_urlsafe(24)
    session[DATA_UPDATE_ACCESS_USER] = session["userid"]
    return redirect(url_for("auth.data_update_selection"))
