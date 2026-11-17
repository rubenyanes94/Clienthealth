"""Cuentas: invitar, restablecer y crear la contraseña con un enlace de un solo uso.

El enlace lleva el secreto después de `#`, así el navegador no lo envía al servidor de la web ni
queda en sus registros. En la base solo se guarda su SHA-256.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta
from html import escape

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import utcnow
from app.models import AccountToken, Agent
from app.models.enums import AccountTokenPurpose
from app.services import email
from app.services.conversations import ConflictError, ConversationError

RESET_THROTTLE = timedelta(seconds=60)
INVALID_LINK = "El enlace no es válido o ya venció. Pida uno nuevo."


@dataclass
class AccessResult:
    email_sent: bool
    dry_run: bool
    error: str | None
    # Solo fuera de producción y sin SMTP: para que el administrador pruebe el flujo.
    link_path: str | None


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def unusable_password() -> str:
    """Para una cuenta invitada: nadie conoce esta clave, así que no se puede entrar con ella."""
    return hash_password(secrets.token_urlsafe(32))


def _issue(db: Session, agent: Agent, purpose: AccountTokenPurpose, actor: Agent | None) -> str:
    now = utcnow()
    # Un enlace nuevo invalida los anteriores: solo vale el último que se envió.
    db.execute(
        update(AccountToken)
        .where(AccountToken.agent_id == agent.id, AccountToken.used_at.is_(None))
        .values(used_at=now)
    )
    settings = get_settings()
    lifetime = (
        timedelta(hours=settings.invite_expire_hours)
        if purpose == AccountTokenPurpose.INVITE
        else timedelta(minutes=settings.reset_expire_minutes)
    )
    token = secrets.token_urlsafe(32)
    db.add(
        AccountToken(
            agent_id=agent.id,
            purpose=purpose,
            token_hash=_hash(token),
            created_by_agent_id=actor.id if actor else None,
            created_at=now,
            expires_at=now + lifetime,
        )
    )
    return token


def _compose(agent: Agent, purpose: AccountTokenPurpose, link: str) -> tuple[str, str, str]:
    settings = get_settings()
    first = agent.name.split()[0]
    if purpose == AccountTokenPurpose.INVITE:
        subject = "Active su cuenta de Atención al Paciente"
        intro = "Le crearon una cuenta en la consola de Atención al Paciente."
        action = "Crear mi contraseña"
        expiry = f"El enlace vence en {settings.invite_expire_hours} horas."
    else:
        subject = "Restablezca su contraseña de Atención al Paciente"
        intro = "Recibimos una solicitud para restablecer su contraseña."
        action = "Restablecer mi contraseña"
        expiry = f"El enlace vence en {settings.reset_expire_minutes} minutos."
    outro = (
        "El enlace solo sirve una vez. Si usted no esperaba este correo, puede ignorarlo: "
        "nadie podrá entrar a su cuenta sin él."
    )
    text = f"Hola, {first}:\n\n{intro}\n\n{action}: {link}\n\n{expiry} {outro}\n"
    html = f"""<div style="font-family:Arial,sans-serif;max-width:480px;color:#0b0b0d">
<p>Hola, {escape(first)}:</p>
<p>{escape(intro)}</p>
<p><a href="{escape(link)}" style="display:inline-block;background:#0b0b0d;color:#fff;
padding:12px 22px;border-radius:999px;text-decoration:none">{escape(action)}</a></p>
<p style="color:#71717a;font-size:13px">{escape(expiry)} {escape(outro)}</p>
<p style="color:#71717a;font-size:13px">Usuario: {escape(agent.email)}</p>
</div>"""
    return subject, text, html


def send_access(
    db: Session, agent: Agent, actor: Agent | None, purpose: AccountTokenPurpose
) -> AccessResult:
    """Emite el enlace y lo envía por correo. El enlace se guarda antes de enviar, para que funcione
    aunque el correo tarde; si el envío falla, se puede reenviar (invalida este)."""
    if not agent.is_active:
        raise ConflictError("La cuenta está desactivada")
    token = _issue(db, agent, purpose, actor)
    db.commit()
    link_path = f"/restablecer#token={token}"
    settings = get_settings()
    subject, text, html = _compose(agent, purpose, settings.app_base_url.rstrip("/") + link_path)
    result = email.send(agent.email, subject, text, html)
    show_link = result.dry_run and not settings.is_production
    error = result.error
    if result.dry_run and settings.is_production:
        error = "No hay servidor de correo configurado (SMTP_HOST)"
    return AccessResult(result.sent, result.dry_run, error, link_path if show_link else None)


def invite_purpose(agent: Agent) -> AccountTokenPurpose:
    return (
        AccountTokenPurpose.INVITE if agent.password_set_at is None else AccountTokenPurpose.RESET
    )


def request_reset(db: Session, email_address: str) -> None:
    """«¿Olvidó su contraseña?». No dice si el correo existe: responde igual en todos los casos."""
    agent = db.scalar(select(Agent).where(Agent.email == email_address.strip().lower()))
    if agent is None or not agent.is_active:
        return
    recent = db.scalar(
        select(AccountToken.id).where(
            AccountToken.agent_id == agent.id,
            AccountToken.created_at > utcnow() - RESET_THROTTLE,
        )
    )
    if recent is not None:  # evita llenarle la bandeja a alguien pulsando muchas veces
        return
    send_access(db, agent, None, invite_purpose(agent))


def _valid(db: Session, token: str) -> AccountToken:
    row = db.scalar(select(AccountToken).where(AccountToken.token_hash == _hash(token)))
    if row is None or row.used_at is not None or row.expires_at <= utcnow():
        raise ConversationError(INVALID_LINK)
    if not row.agent.is_active:
        raise ConversationError(INVALID_LINK)
    return row


def check(db: Session, token: str) -> AccountToken:
    return _valid(db, token)


def set_password(agent: Agent, password: str) -> None:
    """Cierra todas las sesiones abiertas de la persona; la nueva lleva la versión siguiente."""
    agent.password_hash = hash_password(password)
    agent.password_set_at = utcnow()
    agent.session_version = (agent.session_version or 0) + 1


def confirm(db: Session, token: str, password: str) -> Agent:
    row = _valid(db, token)
    agent = row.agent
    set_password(agent, password)
    row.used_at = utcnow()
    db.commit()
    return agent
