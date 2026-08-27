import secrets
from flask import Blueprint, flash, redirect, render_template, request, url_for
from modules.services.auth import admin_required, login_required
from modules.services.db import get_conn

key_approval_bp = Blueprint("key_approval", __name__, template_folder="templates")

def _return_to_approval():
    return redirect(url_for("key_approval.key_approval"))

@key_approval_bp.route("/admin/key-approval")
@login_required
@admin_required
def key_approval():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT application.Application_id, application.UserID, application.Content, application.Usage_days, "
        "application.CreatedAt, COALESCE(NULLIF([user].[Name], ''), N'未設定姓名') AS UserName "
        "FROM dbo.User_applications AS application "
        "LEFT JOIN dbo.Users AS [user] ON application.UserID = [user].UserID "
        "WHERE application.Status = 'Pending' ORDER BY application.CreatedAt ASC"
    )
    columns = [column[0] for column in cursor.description]
    pending_applications = [dict(zip(columns, row)) for row in cursor.fetchall()]
    conn.close()
    return render_template("key_approval.html", active="key_approval", pending_applications=pending_applications)

@key_approval_bp.route("/admin/key-approval/<application_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve(application_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE dbo.User_applications SET Status = 'Approved', API_key = ?, RejectionReason = NULL WHERE Application_id = ? AND Status = 'Pending'", secrets.token_urlsafe(32), application_id)
    conn.commit()
    conn.close()
    flash("申請已核准，等待使用者啟用。", "success")
    return _return_to_approval()


@key_approval_bp.route("/admin/key-approval/<application_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject(application_id):
    reason = request.form.get("reason", "").strip()
    if not reason or len(reason) > 500:
        flash("請填寫 500 字以內的拒絕原因。", "danger")
        return _return_to_approval()
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE dbo.User_applications SET Status = 'Rejected', RejectionReason = ?, API_key = NULL, Start_time = NULL, End_time = NULL WHERE Application_id = ? AND Status = 'Pending'", reason, application_id)
        conn.commit()
    finally:
        conn.close()
    flash("申請已拒絕，原因已通知使用者。", "success")
    return _return_to_approval()


@key_approval_bp.route("/admin/key-approval/<application_id>/reactivate", methods=["POST"])
@login_required
@admin_required
def reactivate(application_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dbo.User_applications SET Status = 'Approved', API_key = ?, "
            "RejectionReason = NULL, Start_time = NULL, End_time = NULL "
            "WHERE Application_id = ? AND Status IN ('Rejected', 'Expired')",
            secrets.token_urlsafe(32), application_id,
        )
        conn.commit()
    finally:
        conn.close()
    flash("Key 已重新啟用，等待使用者啟用。", "success")
    return _return_to_approval()
