import logging
from functools import wraps
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from modules.db import get_conn 

auth_bp = Blueprint('auth', __name__)

# ---- 登入驗證 ----
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

# ---- 管理員權限驗證 ----
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("position") != "Admin":
            flash("權限不足，無法存取此頁面", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "id" in session: 
        return redirect(url_for("dashboard"))    
    if request.method == "POST":
        user_id = request.form["userid"]
        password = request.form["password"]
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT [ID], [UserID], [Password], [Name], [Position], [Location] FROM [dbo].[Users] WHERE UserID = ? AND Password = ?", (user_id, password))
        user = cursor.fetchone()
        
        if user:
            logging.info(f"使用者 {user_id} 登入成功")
            session["id"] = str(user.ID)
            session["userid"] = user.UserID
            session["name"] = user.Name
            session["position"] = user.Position
            session["location"] = user.Location
            cursor.execute("UPDATE [dbo].[Users] SET Last_login = GETDATE() WHERE ID = ?", (user.ID,))
            conn.commit()
            conn.close()
            return redirect("/")          
        conn.close()
        return render_template("login.html", error="帳號或密碼錯誤")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")