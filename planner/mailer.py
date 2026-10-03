"""Send the digest over SMTP. Credentials come from the environment."""

import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage


class MailConfigError(Exception):
    """SMTP settings are missing or unusable."""


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    user: str
    password: str
    sender: str
    recipient: str


RESEND_HOST = "smtp.resend.com"
RESEND_USER = "resend"
RESEND_FROM = "onboarding@resend.dev"


def apply_resend_defaults() -> None:
    """Use Resend's free SMTP relay when only an API key is set."""
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        return
    os.environ.setdefault("SMTP_HOST", RESEND_HOST)
    os.environ.setdefault("SMTP_PORT", "587")
    os.environ.setdefault("SMTP_USER", RESEND_USER)
    os.environ.setdefault("SMTP_PASSWORD", api_key)
    os.environ.setdefault("SMTP_FROM", RESEND_FROM)


def load_smtp(recipient: str) -> SmtpSettings:
    apply_resend_defaults()
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip()
    port_raw = os.environ.get("SMTP_PORT", "587").strip() or "587"
    to = os.environ.get("PLANNER_TO", "").strip() or recipient
    missing = [
        name
        for name, value in (
            ("SMTP_HOST", host),
            ("SMTP_USER", user),
            ("SMTP_PASSWORD", password),
            ("SMTP_FROM", sender),
        )
        if not value
    ]
    if missing:
        raise MailConfigError(
            "Cannot send yet. Set RESEND_API_KEY (see docs/ops/friday-email.md)."
        )
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise MailConfigError(f"SMTP_PORT must be a number, got {port_raw!r}") from exc
    return SmtpSettings(host, port, user, password, sender, to)


def send_email(settings: SmtpSettings, subject: str, text: str, html: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.sender
    message["To"] = settings.recipient
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    try:
        if settings.port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.host, settings.port, timeout=30, context=context) as smtp:
                smtp.login(settings.user, settings.password)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.host, settings.port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(settings.user, settings.password)
                smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise MailConfigError(f"Email failed: {exc}") from exc
