import logging
from functools import wraps
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from modules.services.db import get_conn
from modules.services.audit import write_audit_log
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint('auth', __name__, template_folder='../blueprint/auth/templates')

def password_matches(stored_password, password):
    return check_password_hash(stored_password, password)

def current_session_user():
    user_id = session.get("id")
    if not user_id:
        return None

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [ID], [UserID], [Name], [Position], [Location] FROM [dbo].[Users] WHERE [ID] = ?",(user_id,),)
    user = cursor.fetchone()
    conn.close()
    if not user:
        session.clear()
        return None
    session["userid"] = user.UserID
    session["name"] = user.Name
    session["position"] = user.Position
    session["location"] = user.Location
    return user


# ---- 登入驗證 ----
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_session_user():
            if (request.path.startswith('/api/') or 
                request.path.startswith('/dashboard/upload') or 
                request.path.startswith('/dashboard/delete') or
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                'application/json' in request.headers.get('Accept', '')):
                return jsonify({"ok": False, "error": "請先登入系統"}), 401
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# ---- 管理員權限驗證 ----
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = current_session_user()
        if not user or user.Position != "Admin":
            if (request.path.startswith('/api/') or 
                request.path.startswith('/dashboard/upload') or 
                request.path.startswith('/dashboard/delete') or
                request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
                'application/json' in request.headers.get('Accept', '')):
                return jsonify({"ok": False, "error": "權限不足，需要管理員權限"}), 403
            flash("權限不足，無法存取此頁面", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "id" in session: 
        return redirect(url_for("index"))    
    if request.method == "POST":
        user_id = request.form["userid"]
        password = request.form["password"]
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT [ID], [UserID], [Password], [Name], [Position], [Location] FROM [dbo].[Users] WHERE UserID = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            password_valid = password_matches(user.Password, password)
        else:
            password_valid = False

        if password_valid:
            logging.info(f"使用者 {user_id} 登入成功")
            session.clear()
            session.permanent = True
            session["id"] = str(user.ID)
            session["userid"] = user.UserID
            session["name"] = user.Name
            session["position"] = user.Position
            session["location"] = user.Location
            cursor.execute("UPDATE [dbo].[Users] SET Last_login = GETDATE() WHERE ID = ?", (user.ID,))
            conn.commit()
            conn.close()
            write_audit_log("auth_login_success", {"login_id": user.UserID, "status": "success"}, user_id=str(user.ID), remote_addr=request.remote_addr)
            return redirect("/")          
        conn.close()
        write_audit_log("auth_login_failed", {"login_id": user_id, "status": "failed", "reason": "password_or_account_incorrect"}, remote_addr=request.remote_addr)
        return render_template("login.html", error="帳號或密碼錯誤")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    write_audit_log("auth_logout_success", {"result": "success"})
    session.clear()
    return redirect("/")


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = {
        "ID": session["id"],
        "UserID": session["userid"],
        "Name": session["name"],
        "Position": session["position"],
        "Location": session["location"],
    }
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_password or not new_password:
            flash("請輸入目前密碼與新密碼", "danger")
        elif new_password != confirm_password:
            flash("新密碼與確認密碼不一致", "danger")
        elif len(new_password) < 8:
            flash("新密碼至少需要 8 個字元", "danger")
        else:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT [Password] FROM [dbo].[Users] WHERE [ID] = ?", (user["ID"],))
            password_row = cursor.fetchone()
            password_valid = password_matches(password_row.Password, current_password) if password_row else False
            if password_valid:
                cursor.execute("UPDATE [dbo].[Users] SET [Password] = ? WHERE [ID] = ?", (generate_password_hash(new_password), user["ID"]))
                conn.commit()
                write_audit_log("auth_profile_password_changed", {"target_user": user["UserID"]})
                flash("密碼已更新", "success")
            else:
                flash("目前密碼不正確", "danger")
            conn.close()

    return render_template("profile.html", active="auth.profile", user=user)
