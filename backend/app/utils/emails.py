# Email utilities: send OTPs, password reset links, and verification links.
import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import BackgroundTasks
from app.config import config

#  SMTP configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")


def _send_email(to_email: str, subject: str, body: str, html: str | None = None):
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP_USER and SMTP_PASS must be set in env vars")

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())

    print(f" Email sent to {to_email} (subject: {subject})")


def send_email(background_tasks: BackgroundTasks | None, to_email: str, subject: str, body: str, html: str | None = None):
    if background_tasks:
        background_tasks.add_task(_send_email, to_email, subject, body, html)
    else:
        _send_email(to_email, subject, body, html)


# Email Templates

def send_verification_email(background_tasks: BackgroundTasks | None, to_email: str, token: str):
    verify_link = f"{config.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify Your Email - Scoping Bot"
    body = f"Please verify your email: {verify_link}"
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
      <h2 style="color:#4F46E5;">Welcome to Scoping Bot </h2>
      <p>Hi there,</p>
      <p>Thank you for signing up! Please click the button below to verify your email address:</p>
      <a href="{verify_link}" 
         style="display:inline-block; margin-top:15px; background:#4F46E5; color:white; padding:10px 20px; border-radius:6px; text-decoration:none;">
         Verify Email
      </a>
      <p style="margin-top:20px; font-size:12px; color:#555;">If you did not create this account, please ignore this email.</p>
    </div>
    """
    send_email(background_tasks, to_email, subject, body, html)


def send_reset_password_email(background_tasks: BackgroundTasks | None, to_email: str, token: str):
    reset_link = f"{config.FRONTEND_URL}/reset-password?token={token}"
    subject = " Reset Your Password - Scoping Bot"
    body = f"Click the link to reset your password: {reset_link}"
    html = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px;">
      <h2 style="color:#DC2626;">Reset Your Password</h2>
      <p>Hi there,</p>
      <p>We received a request to reset your password. Click the button below to proceed:</p>
      <a href="{reset_link}" 
         style="display:inline-block; margin-top:15px; background:#DC2626; color:white; padding:10px 20px; border-radius:6px; text-decoration:none;">
         Reset Password
      </a>
      <p style="margin-top:20px; font-size:12px; color:#555;">If you did not request this, you can safely ignore this email.</p>
    </div>
    """
    send_email(background_tasks, to_email, subject, body, html)
