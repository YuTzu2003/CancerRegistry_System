import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from modules.db import get_conn
from services.auth import login_required, admin_required

member_bp = Blueprint('member', __name__)

@member_bp.route("/member")
@login_required
@admin_required
def member():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [ID], [UserID], [Password], [Name], [Position], [Location], [Last_login] FROM [dbo].[Users] ORDER BY UserID")
    columns = [column[0] for column in cursor.description]
    users = [dict(zip(columns, row)) for row in cursor.fetchall()]
    for u in users:
        u['ID'] = str(u['ID'])
        if u['Last_login'] and isinstance(u['Last_login'], datetime.datetime):
            u['Last_login'] = u['Last_login'].strftime("%Y/%m/%d %H:%M:%S")
    conn.close()
    return render_template("member.html", active="member", users=users)

@member_bp.route("/member/tool", methods=["POST"])
@login_required
@admin_required
def admin_save_user():
    user_db_id = request.form.get("id")
    user_id = request.form.get("UserID")
    password = request.form.get("Password")
    name = request.form.get("Name")
    position = request.form.get("Position")
    location = request.form.get("Location")

    conn = get_conn()
    cursor = conn.cursor()
    if user_db_id:
        cursor.execute("UPDATE [dbo].[Users] SET [UserID]=?, [Password]=?, [Name]=?, [Position]=?, [Location]=? WHERE [ID]=?", (user_id, password, name, position, location, user_db_id))
        flash(f"使用者 {name} 資料已更新", "success")
    else:
        cursor.execute("INSERT INTO [dbo].[Users] ([UserID], [Password], [Name], [Position], [Location]) VALUES (?, ?, ?, ?, ?)", (user_id, password, name, position, location))
        flash(f"成功新增使用者 {name}", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("member.member"))

@member_bp.route("/member/delete/<user_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Users] WHERE [ID]=?", (user_id,))
    conn.commit()
    conn.close()
    flash("使用者已成功刪除", "success")
    return redirect(url_for("member.member"))
