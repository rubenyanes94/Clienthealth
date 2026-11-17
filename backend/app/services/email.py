"""Envío de correos por SMTP (sirve con casi cualquier proveedor). Sin dependencias externas.

Nunca se loguea el contenido ni los enlaces: solo si se envió o por qué falló.
"""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger(__name__)


@dataclass
class EmailResult:
    sent: bool
    dry_run: bool = False  # no hay SMTP configurado: no se intentó enviar
    error: str | None = None


def send(to: str, subject: str, text: str, html: str) -> EmailResult:
    settings = get_settings()
    if not settings.smtp_host:
        return EmailResult(sent=False, dry_run=True)
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        log.warning("correo no enviado: %s", type(exc).__name__)
        return EmailResult(sent=False, error="El servidor de correo no aceptó el envío")
    return EmailResult(sent=True)
