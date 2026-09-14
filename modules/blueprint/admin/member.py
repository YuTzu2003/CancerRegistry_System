import datetime
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from modules.services.db import get_conn
from modules.services.audit import write_audit_log
from modules.services.auth import login_required, admin_required
from werkzeug.security import generate_password_hash

member_bp = Blueprint('member', __name__, template_folder='templates')

@member_bp.route("/member")
@login_required
@admin_required
def member():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT [ID], [UserID], [Name], [Position], [Location], [Last_login] FROM [dbo].[Users] ORDER BY UserID")
    columns = [column[0] for column in cursor.description]
    users = [dict(zip(columns, row)) for row in cursor.fetchall()]
    for u in users:
        u['ID'] = str(u['ID'])
        if u['Last_login'] and isinstance(u['Last_login'], datetime.datetime):
            u['Last_login'] = u['Last_login'].strftime("%Y/%m/%d %H:%M:%S")
            
    # Login results are stored in dbo.Audit_logs so deployments do not depend on local files.
    cursor.execute("SELECT audit.[CreatedAt] AS login_time, audit.[Action], audit.[User_id], audit.[detail_json], audit.[Remote_addr] AS ip, [user].[UserID], [user].[Name], [user].[Position] FROM dbo.Audit_logs AS audit LEFT JOIN dbo.Users AS [user] ON CONVERT(varchar(36), [user].[ID]) = audit.[User_id] WHERE audit.[Action] IN ('auth_login_success', 'auth_login_failed') ORDER BY audit.[CreatedAt] DESC")
    login_columns = [column[0] for column in cursor.description]
    login_logs = []
    for row in cursor.fetchall():
        log = dict(zip(login_columns, row))
        try:
            detail = json.loads(log["detail_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            detail = {}
        login_time = log["login_time"]
        login_logs.append({
            "login_time": login_time.strftime("%Y/%m/%d %H:%M:%S") if isinstance(login_time, datetime.datetime) else login_time,
            "userid": log["UserID"] or detail.get("login_id", "-"),
            "Name": log["Name"] or "未知",
            "Position": log["Position"] or "未知角色",
            "ip": log["ip"] or "-",
            "success": log["Action"] == "auth_login_success",
            "reason": "登入成功" if log["Action"] == "auth_login_success" else detail.get("reason", "帳號或密碼錯誤"),
        })

    conn.close()
    return render_template("member.html",active="member",users=users,login_logs=login_logs,)

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
        if password:
            cursor.execute("UPDATE [dbo].[Users] SET [UserID]=?, [Password]=?, [Name]=?, [Position]=?, [Location]=? WHERE [ID]=?", (user_id, generate_password_hash(password), name, position, location, user_db_id))
        else:
            cursor.execute("UPDATE [dbo].[Users] SET [UserID]=?, [Name]=?, [Position]=?, [Location]=? WHERE [ID]=?", (user_id, name, position, location, user_db_id))
        flash(f"使用者 {name} 資料已更新", "success")
    elif not password:
        conn.close()
        flash("新增使用者時必須設定密碼", "danger")
        return redirect(url_for("member.member"))
    else:
        cursor.execute("INSERT INTO [dbo].[Users] ([UserID], [Password], [Name], [Position], [Location]) VALUES (?, ?, ?, ?, ?)", (user_id, generate_password_hash(password), name, position, location))
        flash(f"成功新增使用者 {name}", "success")
    conn.commit()
    conn.close()
    action = "member_member_update" if user_db_id else "member_member_create"
    write_audit_log(action, {"target_user": user_id, "name": name, "position": position, "location": location})
    return redirect(url_for("member.member"))

@member_bp.route("/member/delete/<user_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_user(user_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM [dbo].[Users] WHERE [ID]=?", (user_id,))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted:
        write_audit_log("member_member_delete", {"target_user_id": user_id})
    flash("使用者已成功刪除", "success")
    return redirect(url_for("member.member"))