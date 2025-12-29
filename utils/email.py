from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from core.config import settings
from starlette.requests import Request
import asyncio

conf = ConnectionConfig(
    MAIL_USERNAME=settings.SMTP_USERNAME or "",
    MAIL_PASSWORD=settings.SMTP_PASSWORD or "",
    MAIL_FROM=settings.SMTP_FROM_EMAIL,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False # Set to True in production with proper certs
)

async def send_verification_email(email_to: str, otp: str):
    """
    Sends a verification email with OTP using fastapi-mail (Async).
    If SMTP settings are not configured properly, it prints the OTP to the console.
    """
    
    subject = "Your Verification OTP for Xplor"
    body = f"Your verification code is: {otp}"
    
    # Check if SMTP settings are present
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print(f"\n[MOCK EMAIL] To: {email_to}")
        print(f"[MOCK EMAIL] Subject: {subject}")
        print(f"[MOCK EMAIL] Body: {body}\n")
        return

    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype=MessageType.plain
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message)
    except Exception as e:
        print(f"Failed to send email: {e}")
