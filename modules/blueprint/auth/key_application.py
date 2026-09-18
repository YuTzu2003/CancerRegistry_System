from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from modules.services.auth import login_required
from modules.services.db import get_conn

key_application_bp = Blueprint("key_application", __name__, template_folder="templates")

def _return_to_applications():
    return redirect(url_for("key_application.application"))

def _application_columns(cursor):
    return [column[0] for column in cursor.description]

@key_application_bp.route("/auth/key-applications")
@login_required
def application():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE dbo.User_applications SET Status = 'Expired' WHERE Status = 'Active' AND End_time < GETDATE()")
    cursor.execute("SELECT Application_id, Content, Usage_days, Status, Start_time, End_time, API_key, CreatedAt, RejectionReason FROM dbo.User_applications WHERE UserID = ? ORDER BY CreatedAt DESC", session["userid"])
    applications = [dict(zip(_application_columns(cursor), row)) for row in cursor.fetchall()]
    conn.commit()
    conn.close()
    for item in applications:
        key = item.pop("API_key", None)
        item["masked_key"] = f"{'*' * 8}{key[-4:]}" if key else "—"
    return render_template("key_application.html", active="application", applications=applications)

@key_application_bp.route("/auth/key-applications", methods=["POST"])
@login_required
def create_application():
    content = request.form.get("content", "").strip()
    usage_days = request.form.get("usage_days", "").strip()
    if not content or len(content) > 50:
        flash("請填寫 50 字以內的申請需求。", "danger")
        return _return_to_applications()
    if not usage_days.isdigit() or not 1 <= int(usage_days) <= 30:
        flash("借用時間須為1至30天。", "danger")
        return _return_to_applications()

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO dbo.User_applications (UserID, Content, Usage_days, Status) VALUES (?, ?, ?, 'Pending')",session["userid"], content, int(usage_days),)
    conn.commit()
    conn.close()
    flash("權限申請已送出，請等待管理員審核。", "success")
    return _return_to_applications()


@key_application_bp.route("/auth/key-applications/<application_id>/activate", methods=["POST"])
@login_required
def activate_application(application_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE dbo.User_applications SET Status = 'Active', Start_time = GETDATE(), End_time = DATEADD(day, Usage_days, GETDATE()) WHERE Application_id = ? AND UserID = ? AND Status = 'Approved'", application_id, session["userid"])
    conn.commit()
    conn.close()
    flash("Key 已啟用，借用時間已開始計算。", "success")
    return _return_to_applications()

@key_application_bp.route("/auth/key-applications/<application_id>/delete", methods=["POST"])
@login_required
def delete_application(application_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM dbo.User_applications WHERE Application_id = ? AND UserID = ? AND Status = 'Pending'", application_id, session["userid"])
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted:
        flash("申請紀錄已刪除。", "success")
    else:
        flash("管理員已審核的申請不可刪除。", "warning")
    return _return_to_applications()

@key_application_bp.route("/auth/key-applications/<application_id>/key")
@login_required
def copy_key(application_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT API_key FROM dbo.User_applications WHERE Application_id = ? AND UserID = ? AND (Status = 'Approved' OR (Status = 'Active' AND End_time >= GETDATE()))", application_id, session["userid"])
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        return jsonify({"error": "找不到可複製的 Key。"}), 404
    return jsonify({"key": row[0]})
