"""Gmail SMTP delivery for account verification codes.
No credentials or verification codes are logged by this module.
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def _enabled(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def email_verification_enabled() -> bool:
    return _enabled("EMAIL_VERIFICATION_ENABLED") and _enabled("GMAIL_SMTP_ENABLED")


def send_verification_code(recipient: str, code: str, purpose: str, minutes: int) -> tuple[bool, str]:
    """Deliver a six-digit code through Gmail SMTP.  Returns no secret data."""
    if not email_verification_enabled():
        return False, "Email 驗證服務目前未啟用。"

    sender = os.getenv("GMAIL_SENDER_EMAIL", "").strip()
    app_password = os.getenv("GMAIL_SMTP_APP_PASSWORD", "")
    if not sender or not app_password:
        return False, "Email 寄送設定尚未完成，請聯絡資訊室。"

    action = "重設密碼" if purpose == "PASSWORD_RESET" else "綁定 Email"
    message = EmailMessage()
    message["Subject"] = f"癌症登記資料平台｜{action}驗證碼"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"您正在進行{action}。\n\n"
        f"驗證碼：{code}\n"
        f"此驗證碼將於 {minutes} 分鐘後失效，請勿轉寄或提供給任何人。\n\n"
        "若非您本人操作，請忽略此信件。"
    )
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            smtp.login(sender, app_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        return False, "Email 無法寄出，請稍後再試或聯絡資訊室。"
    return True, "驗證碼已寄出。"