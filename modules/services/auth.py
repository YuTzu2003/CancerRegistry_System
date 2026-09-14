import datetime
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
from functools import wraps

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from modules.services.db import get_conn
from .email_verification import email_verification_enabled, send_verification_code


auth_bp = Blueprint('auth', __name__, template_folder='../blueprint/auth/templates')

CODE_PURPOSE_EMAIL_BIND = 'EMAIL_BIND'
CODE_PURPOSE_PASSWORD_RESET = 'PASSWORD_RESET'
CODE_MAX_ATTEMPTS = 5
EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def _positive_int(name, default):
    try:
        return max(1, int(os.getenv(name, default)))
    except (TypeError, ValueError):
        return default


def _feature_enabled():
    return os.getenv('EMAIL_VERIFICATION_ENABLED', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}


def _normalize_email(value):
    email = str(value or '').strip().lower()
    return email if EMAIL_PATTERN.fullmatch(email) else ''


def login_log(user_id, ip, success, reason=''):
    log_dir = 'tasks/cache'
    os.makedirs(log_dir, exist_ok=True)
    log_entry = {
        'userid': user_id,
        'ip': ip,
        'login_time': datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S'),
        'success': success,
        'reason': reason,
    }
    with open(f'{log_dir}/login_logs.json', 'a', encoding='utf-8') as handle:
        handle.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
from modules.services.audit import write_audit_log
from modules.config import BaseConfig
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint('auth', __name__, template_folder='../blueprint/auth/templates')

def password_matches(stored_password, password):
    return check_password_hash(stored_password, password)


def _login_rate_limited(remote_addr):
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dbo.Audit_logs WHERE [Action] = ? AND [Remote_addr] = ? AND [CreatedAt] >= DATEADD(second, ?, SYSDATETIMEOFFSET())", ("auth_login_failed", remote_addr or "", -BaseConfig.LOGIN_ATTEMPT_WINDOW_SECONDS))
        row = cursor.fetchone()
        return bool(row and int(row[0]) >= BaseConfig.LOGIN_MAX_ATTEMPTS)
    except Exception:
        logging.exception("Unable to check login rate limit")
        return False
    finally:
        conn.close()

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

def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'id' not in session:
            if (request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    or 'application/json' in request.headers.get('Accept', '')):
                return jsonify({'ok': False, 'error': '請先登入系統'}), 401
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return decorated_function


def admin_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if session.get('position') != 'Admin':
            if request.path.startswith('/api/') or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'ok': False, 'error': '權限不足，需要管理員權限'}), 403
            flash('權限不足，無法存取此頁面', 'danger')
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return decorated_function


def _fetch_user(*, user_id=None, db_id=None):
    if not user_id and not db_id:
        return None
    query = '''
        SELECT [ID], [UserID], [Password], [Name], [Position], [Location],
               [Email], [EmailVerifiedAt], [EmailPromptDismissedAt]
        FROM dbo.Users WHERE ''' + ('[UserID] = ?' if user_id else '[ID] = ?')
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (user_id if user_id else db_id,))
        row = cursor.fetchone()
        if not row:
            return None
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, row))
    finally:
        conn.close()
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
        if _login_rate_limited(request.remote_addr):
            return render_template("login.html", error="登入嘗試次數過多，請稍後再試。"), 429
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


def _hash_code(code, salt, user_db_id, purpose):
    value = f'{salt}:{user_db_id}:{purpose}:{code}'.encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def _issue_code(user, email, purpose):
    if not email_verification_enabled():
        return False, 'Email 驗證服務目前未啟用，請聯絡資訊室。'

    resend_seconds = _positive_int('VERIFICATION_CODE_RESEND_SECONDS', 60)
    max_per_hour = _positive_int('VERIFICATION_CODE_MAX_PER_HOUR', 5)
    minutes = _positive_int('PASSWORD_CODE_MINUTES', 10)
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM dbo.AccountVerificationCodes
            WHERE UserID = ? AND Purpose = ? AND CreatedAt >= DATEADD(hour, -1, GETDATE())
        ''', (str(user['ID']), purpose))
        if int(cursor.fetchone()[0] or 0) >= max_per_hour:
            return False, '此帳號一小時內已達驗證碼寄送上限，請稍後再試。'

        cursor.execute('''
            SELECT TOP 1 CreatedAt FROM dbo.AccountVerificationCodes
            WHERE UserID = ? AND Purpose = ? ORDER BY CreatedAt DESC
        ''', (str(user['ID']), purpose))
        previous = cursor.fetchone()
        if previous and (datetime.datetime.now() - previous[0]).total_seconds() < resend_seconds:
            return False, f'請於 {resend_seconds} 秒後再重新寄送驗證碼。'

        code = f'{secrets.randbelow(1_000_000):06d}'
        salt = secrets.token_hex(16)
        code_hash = _hash_code(code, salt, user['ID'], purpose)
        cursor.execute('''
            UPDATE dbo.AccountVerificationCodes SET InvalidatedAt = GETDATE()
            WHERE UserID = ? AND Purpose = ? AND ConsumedAt IS NULL AND InvalidatedAt IS NULL
        ''', (str(user['ID']), purpose))
        cursor.execute('''
            INSERT INTO dbo.AccountVerificationCodes
                (UserID, Email, Purpose, CodeSalt, CodeHash, ExpiresAt)
            VALUES (?, ?, ?, ?, ?, DATEADD(minute, ?, GETDATE()))
        ''', (str(user['ID']), email, purpose, salt, code_hash, minutes))
        conn.commit()
    except Exception:
        conn.rollback()
        logging.exception('Unable to issue account verification code.')
        return False, '無法建立驗證碼，請稍後再試或聯絡資訊室。'
    finally:
        conn.close()

    delivered, message = send_verification_code(email, code, purpose, minutes)
    if delivered:
        return True, message

    # The code must not remain usable when delivery failed.
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE dbo.AccountVerificationCodes SET InvalidatedAt = GETDATE()
            WHERE UserID = ? AND Purpose = ? AND CodeHash = ? AND ConsumedAt IS NULL
        ''', (str(user['ID']), purpose, code_hash))
        conn.commit()
    finally:
        conn.close()
    return False, message


def _consume_code(user, email, purpose, code):
    supplied = str(code or '').strip()
    if not re.fullmatch(r'\d{6}', supplied):
        return False, '請輸入六位數驗證碼。'
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT TOP 1 VerificationCodeID, CodeSalt, CodeHash, AttemptCount
            FROM dbo.AccountVerificationCodes
            WHERE UserID = ? AND Email = ? AND Purpose = ?
              AND ConsumedAt IS NULL AND InvalidatedAt IS NULL
              AND ExpiresAt > GETDATE()
            ORDER BY CreatedAt DESC
        ''', (str(user['ID']), email, purpose))
        row = cursor.fetchone()
        if not row:
            return False, '驗證碼無效或已過期，請重新寄送。'

        verification_id, salt, stored_hash, attempt_count = row
        candidate_hash = _hash_code(supplied, salt, user['ID'], purpose)
        if not hmac.compare_digest(candidate_hash, stored_hash):
            next_attempt = int(attempt_count or 0) + 1
            cursor.execute('UPDATE dbo.AccountVerificationCodes SET AttemptCount = ? WHERE VerificationCodeID = ?', (next_attempt, str(verification_id)))
            if next_attempt >= CODE_MAX_ATTEMPTS:
                cursor.execute('UPDATE dbo.AccountVerificationCodes SET InvalidatedAt = GETDATE() WHERE VerificationCodeID = ?', (str(verification_id),))
            conn.commit()
            return False, '驗證碼錯誤，請再確認。'

        cursor.execute('UPDATE dbo.AccountVerificationCodes SET ConsumedAt = GETDATE() WHERE VerificationCodeID = ?', (str(verification_id),))
        conn.commit()
        return True, ''
    except Exception:
        conn.rollback()
        logging.exception('Unable to validate account verification code.')
        return False, '驗證碼驗證失敗，請稍後再試。'
    finally:
        conn.close()


def _email_in_use(email, current_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM dbo.Users WHERE Email = ? AND ID <> ?', (email, str(current_id)))
        return cursor.fetchone() is not None
    finally:
        conn.close()


def _set_email(user_id, email=None, *, dismissed=False):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        if email:
            cursor.execute('''
                UPDATE dbo.Users
                SET Email = ?, EmailVerifiedAt = GETDATE(), EmailPromptDismissedAt = NULL
                WHERE ID = ?
            ''', (email, str(user_id)))
        else:
            cursor.execute('''
                UPDATE dbo.Users
                SET Email = NULL, EmailVerifiedAt = NULL,
                    EmailPromptDismissedAt = CASE WHEN ? = 1 THEN GETDATE() ELSE NULL END
                WHERE ID = ?
            ''', (1 if dismissed else 0, str(user_id)))
        conn.commit()
    finally:
        conn.close()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        user_id = request.form.get('userid', '').strip()
        password = request.form.get('password', '')
        user = _fetch_user(user_id=user_id)
        if user and hmac.compare_digest(str(user['Password'] or ''), password):
            logging.info('User %s logged in.', user_id)
            login_log(user_id, request.remote_addr, True, '登入成功')
            session['id'] = str(user['ID'])
            session['userid'] = user['UserID']
            session['name'] = user['Name']
            session['position'] = user['Position']
            session['location'] = user['Location']
            conn = get_conn()
            try:
                cursor = conn.cursor()
                cursor.execute('UPDATE dbo.Users SET Last_login = GETDATE() WHERE ID = ?', (str(user['ID']),))
                conn.commit()
            finally:
                conn.close()
            if (_feature_enabled() and user['Position'] != 'Admin' and not user['Email']
                    and not user['EmailPromptDismissedAt']):
                return redirect(url_for('auth.email_binding_prompt'))
            return redirect(url_for('index'))
        login_log(user_id, request.remote_addr, False, '帳號或密碼錯誤')
        return render_template('login.html', error='帳號或密碼錯誤')
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    write_audit_log("auth_logout_success", {"result": "success"})
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/account/email', methods=['GET', 'POST'])
@login_required
def account_email():
    user = _fetch_user(db_id=session['id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        action = request.form.get('action', '')
        if action == 'send_bind':
            email = _normalize_email(request.form.get('email'))
            if not email:
                flash('請輸入有效的 Email 地址。', 'danger')
            elif _email_in_use(email, user['ID']):
                flash('此 Email 已被其他帳號綁定。', 'danger')
            else:
                sent, message = _issue_code(user, email, CODE_PURPOSE_EMAIL_BIND)
                if sent:
                    session['pending_bind_email'] = email
                    flash(message, 'success')
                else:
                    flash(message, 'danger')
            return redirect(url_for('auth.account_email'))

        if action == 'verify_bind':
            email = session.get('pending_bind_email', '')
            if not email:
                flash('請先輸入 Email 並寄送驗證碼。', 'warning')
            elif _email_in_use(email, user['ID']):
                flash('此 Email 已被其他帳號綁定。', 'danger')
            else:
                valid, message = _consume_code(user, email, CODE_PURPOSE_EMAIL_BIND, request.form.get('code'))
                if valid:
                    _set_email(user['ID'], email)
                    session.pop('pending_bind_email', None)
                    flash('Email 已完成綁定。', 'success')
                else:
                    flash(message, 'danger')
            return redirect(url_for('auth.account_email'))

        if action == 'cancel_bind':
            _set_email(user['ID'], dismissed=True)
            session.pop('pending_bind_email', None)
            flash('已取消 Email 綁定。', 'success')
            return redirect(url_for('auth.account_email'))

    return render_template(
        'account_email.html', active='account_email', user=user,
        pending_email=session.get('pending_bind_email', ''),
        email_enabled=email_verification_enabled(),
    )


@auth_bp.route('/account/email/prompt', methods=['GET', 'POST'])
@login_required
def email_binding_prompt():
    user = _fetch_user(db_id=session['id'])
    if not user or user['Position'] == 'Admin' or user['Email'] or user['EmailPromptDismissedAt']:
        return redirect(url_for('index'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'dismiss':
            _set_email(user['ID'], dismissed=True)
            flash('已記錄設定；之後仍可從帳號 Email 設定頁綁定。', 'info')
            return redirect(url_for('index'))
        return redirect(url_for('auth.account_email'))
    return render_template('email_binding_prompt.html', active='account_email', email_enabled=email_verification_enabled())


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        user = _fetch_user(user_id=request.form.get('userid', '').strip())
        if not user:
            flash('查無此帳號。', 'danger')
        elif not user['Email'] or not user['EmailVerifiedAt']:
            flash('此帳號尚未綁定 Email，請聯絡資訊室協助重設密碼。', 'warning')
        else:
            sent, message = _issue_code(user, user['Email'], CODE_PURPOSE_PASSWORD_RESET)
            if sent:
                session['password_reset_user_id'] = str(user['ID'])
                flash(message, 'success')
                return redirect(url_for('auth.reset_password'))
            flash(message, 'danger')
    return render_template('forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    user_db_id = session.get('password_reset_user_id')
    if not user_db_id:
        flash('請先申請密碼重設驗證碼。', 'warning')
        return redirect(url_for('auth.forgot_password'))
    user = _fetch_user(db_id=user_db_id)
    if not user or not user['Email'] or not user['EmailVerifiedAt']:
        session.pop('password_reset_user_id', None)
        flash('帳號 Email 綁定狀態已變更，請重新申請。', 'warning')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        if len(password) < 8:
            flash('新密碼至少需 8 個字元。', 'danger')
        elif password != confirm_password:
            flash('兩次輸入的新密碼不一致。', 'danger')
        else:
            valid, message = _consume_code(user, user['Email'], CODE_PURPOSE_PASSWORD_RESET, request.form.get('code'))
            if valid:
                conn = get_conn()
                try:
                    cursor = conn.cursor()
                    cursor.execute('UPDATE dbo.Users SET Password = ? WHERE ID = ?', (password, str(user['ID'])))
                    conn.commit()
                finally:
                    conn.close()
                session.pop('password_reset_user_id', None)
                flash('密碼已重設，請使用新密碼登入。', 'success')
                return redirect(url_for('auth.login'))
            flash(message, 'danger')
    return render_template('reset_password.html', userid=user['UserID'])
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
