"""
Email Verification & OTP Dispatch Service for VibeSplit.
Supports real SMTP (Gmail, SendGrid, Mailgun, Resend, etc.) + Dev Fallback.
"""
import os
import random
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

logger = logging.getLogger("vibesplit.email")

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "no-reply@vibesplit.io")

def generate_otp_code() -> str:
    """Generate a random 6-digit verification code."""
    return f"{random.randint(100000, 999999)}"

def send_verification_email(to_email: str, otp_code: str, full_name: str = "Friend") -> bool:
    """
    Sends a Gen-Z styled HTML verification email with the 6-digit OTP code.
    If SMTP credentials are not configured, logs to console and returns True.
    """
    logger.info(f"🔑 [OTP Generated for {to_email}]: {otp_code}")

    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.info(f"ℹ️ SMTP not configured. OTP [{otp_code}] logged to server output.")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"⚡ {otp_code} is your VibeSplit Verification Code"
        msg["From"] = f"VibeSplit ⚡ <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F8FAFC; color: #0F172A; padding: 20px; }}
            .card {{ max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 24px; padding: 32px; box-shadow: 0 10px 25px rgba(124, 58, 237, 0.08); border: 1px solid #E2E8F0; text-align: center; }}
            .logo {{ font-size: 32px; margin-bottom: 12px; }}
            h2 {{ color: #0F172A; font-size: 22px; margin-bottom: 8px; font-weight: 800; }}
            p {{ color: #475569; font-size: 14px; line-height: 1.5; margin: 8px 0; }}
            .otp-box {{ display: inline-block; background: #F3E8FF; border: 2px dashed #9333EA; color: #7C3AED; font-size: 32px; font-weight: 900; letter-spacing: 6px; padding: 14px 28px; border-radius: 16px; margin: 24px 0; }}
            .footer {{ font-size: 12px; color: #94A3B8; margin-top: 24px; }}
          </style>
        </head>
        <body>
          <div class="card">
            <div class="logo">⚡</div>
            <h2>Verify Your VibeSplit Account</h2>
            <p>Hey {full_name}! 👋 Welcome to VibeSplit. Use the 6-digit code below to verify your email and activate your account:</p>
            
            <div class="otp-box">{otp_code}</div>
            
            <p style="font-size: 12px; color: #64748B;">⏱️ This verification code is valid for <strong>10 minutes</strong>. If you didn't request this code, you can safely ignore this email.</p>
            
            <div class="footer">
              Split tabs, roast debts & keep the vibe intact 💅✨<br>
              &copy; {datetime.now().year} VibeSplit
            </div>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"✅ Real verification email successfully sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to dispatch SMTP email to {to_email}: {e}")
        return False
