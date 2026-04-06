"""Email service — sends emails via SMTP or logs them in dev mode.

Configure via environment:
  HUBEX_SMTP_HOST=smtp.gmail.com
  HUBEX_SMTP_PORT=587
  HUBEX_SMTP_USER=your@email.com
  HUBEX_SMTP_PASSWORD=your_password
  HUBEX_SMTP_FROM=noreply@hubex.io
  HUBEX_SMTP_TLS=true
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("uvicorn.error")

SMTP_HOST = os.getenv("HUBEX_SMTP_HOST", "")
SMTP_PORT = int(os.getenv("HUBEX_SMTP_PORT", "587"))
SMTP_USER = os.getenv("HUBEX_SMTP_USER", "")
SMTP_PASSWORD = os.getenv("HUBEX_SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("HUBEX_SMTP_FROM", "noreply@hubex.io")
SMTP_TLS = os.getenv("HUBEX_SMTP_TLS", "true").lower() == "true"


def is_configured() -> bool:
    """Check if SMTP is configured."""
    return bool(SMTP_HOST and SMTP_USER)


def send_email(to: str, subject: str, body_html: str, body_text: str | None = None) -> bool:
    """Send an email. Returns True on success, False on failure.

    If SMTP is not configured, logs the email instead of sending.
    """
    if not is_configured():
        logger.info(
            "email (dev mode): to=%s subject=%s body=%s",
            to, subject, (body_text or body_html)[:100],
        )
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to

        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_TLS:
                server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())

        logger.info("email sent: to=%s subject=%s", to, subject)
        return True
    except Exception as e:
        logger.error("email failed: to=%s error=%s", to, e)
        return False
