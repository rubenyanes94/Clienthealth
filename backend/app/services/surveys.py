"""Encuestas CSAT (al cerrar) y NPS (muestreo mensual), y captura de sus respuestas.

Solo se guarda la puntuación. Las encuestas se envían como plantillas aprobadas porque pueden salir
fuera de la ventana de 24 h.
"""

import logging
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from app.core.config import get_settings
from app.db.base import utcnow
from app.models import Agent, Contact, Conversation, Message, Survey
from app.models.enums import (
    ConversationStatus,
    EventType,
    MessageDirection,
    MessageStatus,
    SenderType,
    SurveyKind,
    SurveyStatus,
)
from app.services import events
from app.services.outbound import send_message, send_template

logger = logging.getLogger(__name__)

SCALE = {SurveyKind.CSAT: (1, 5), SurveyKind.NPS: (0, 10)}

# Texto que ve el agente en el chat; el contenido real lo define la plantilla aprobada en Meta.
PREVIEW = {
    SurveyKind.CSAT: "[Plantilla] Encuesta de satisfacción: califique la atención del 1 al 5.",
    SurveyKind.NPS: "[Plantilla] Del 0 al 10, ¿qué tan probable es que nos recomiende?",
}
THANKS = "¡Gracias por su respuesta! Nos ayuda a mejorar la atención."

_NUMBER = re.compile(r"\s*(\d{1,2})\s*(?:/\s*(?:5|10))?\s*(?:puntos?)?\s*[.!]*\s*")


def parse_score(text: str, kind: SurveyKind) -> int | None:
    """ "4", "4/5", "⭐⭐⭐⭐" o la etiqueta del botón de la plantilla."""
    low, high = SCALE[kind]
    stripped = text.strip()
    if kind == SurveyKind.CSAT and stripped and set(stripped) <= {"⭐", "★", " "}:
        score = stripped.count("⭐") + stripped.count("★")
    elif match := _NUMBER.fullmatch(text):
        score = int(match.group(1))
    else:
        return None
    return score if low <= score <= high else None


def _template(kind: SurveyKind) -> str:
    settings = get_settings()
    return (
        settings.whatsapp_csat_template
        if kind == SurveyKind.CSAT
        else (settings.whatsapp_nps_template)
    )


def _send(db: Session, conversation: Conversation, kind: SurveyKind, agent: Agent | None) -> Survey:
    message = send_template(db, conversation, _template(kind), PREVIEW[kind])
    failed = message.status == MessageStatus.FAILED
    survey = Survey(
        conversation_id=conversation.id,
        contact_id=conversation.contact_id,
        agent_id=agent.id if agent else None,
        kind=kind,
        status=SurveyStatus.FAILED if failed else SurveyStatus.SENT,
        message_id=message.id,
        sent_at=utcnow(),
    )
    db.add(survey)
    db.flush()
    if not failed:
        events.record(
            db,
            conversation,
            EventType.SURVEY_SENT,
            agent=agent,
            data={"survey_id": survey.id, "kind": kind.value},
        )
    return survey


def csat_skip_reason(db: Session, conversation: Conversation) -> str | None:
    """Por qué no se enviaría la CSAT al cerrar este caso (None = se envía)."""
    if conversation.is_urgent:
        return "urgent"  # no se pide calificación tras una urgencia
    cutoff = utcnow() - timedelta(days=get_settings().survey_cooldown_days)
    recent = db.scalar(
        select(Survey.id).where(
            Survey.contact_id == conversation.contact_id,
            Survey.kind == SurveyKind.CSAT,
            Survey.status != SurveyStatus.FAILED,
            Survey.sent_at >= cutoff,
        )
    )
    return "cooldown" if recent else None


def maybe_send_csat(db: Session, conversation: Conversation, agent: Agent) -> Survey | None:
    if csat_skip_reason(db, conversation) is not None:
        return None
    return _send(db, conversation, SurveyKind.CSAT, agent)


def _pending_survey(db: Session, contact: Contact) -> Survey | None:
    window = timedelta(hours=get_settings().survey_answer_window_hours)
    return db.scalar(
        select(Survey)
        .where(
            Survey.contact_id == contact.id,
            Survey.status == SurveyStatus.SENT,
            Survey.sent_at >= utcnow() - window,
        )
        .order_by(Survey.id.desc())
        .limit(1)
        .with_for_update()
    )


def capture_answer(
    db: Session, contact: Contact, text: str, kind_of_message: str, wamid: str
) -> bool:
    """Si el mensaje responde a una encuesta pendiente, la registra y devuelve True.

    Solo se interpreta como respuesta si el paciente no tiene otra conversación activa (así un "5"
    en el menú del bot nunca se toma como calificación). Cualquier otro mensaje vence la encuesta.
    """
    survey = _pending_survey(db, contact)
    if survey is None:
        return False

    has_active = db.scalar(
        select(Conversation.id).where(
            Conversation.contact_id == contact.id,
            Conversation.status != ConversationStatus.CLOSED,
        )
    )
    score = None if has_active else parse_score(text, survey.kind)
    if score is None:
        survey.status = SurveyStatus.EXPIRED
        return False

    now = utcnow()
    conversation = db.get(Conversation, survey.conversation_id, with_for_update=True)
    message = Message(
        conversation_id=conversation.id,
        direction=MessageDirection.INBOUND,
        sender_type=SenderType.CONTACT,
        message_type=kind_of_message,
        body=text,
        external_id=wamid,
        status=MessageStatus.RECEIVED,
        created_at=now,
    )
    db.add(message)
    db.flush()
    conversation.last_inbound_at = now
    conversation.last_message_at = now
    survey.status = SurveyStatus.ANSWERED
    survey.score = score
    survey.answered_at = now
    events.record(
        db,
        conversation,
        EventType.INBOUND_MESSAGE,
        data={"message_id": message.id, "survey_id": survey.id},
    )
    events.record(
        db,
        conversation,
        EventType.SURVEY_ANSWERED,
        data={"survey_id": survey.id, "kind": survey.kind.value, "score": score},
    )
    reply = send_message(db, conversation, THANKS, sender_type=SenderType.SYSTEM)
    events.record(db, conversation, EventType.BOT_MESSAGE, data={"message_id": reply.id})
    return True


def _month_start_utc(now: datetime) -> datetime:
    local = now.astimezone(ZoneInfo(get_settings().timezone))
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def run_monthly_nps(db: Session, now: datetime | None = None) -> int:
    """Envía la NPS a una muestra aleatoria el día configurado. Idempotente dentro del mes."""
    settings = get_settings()
    now = now or utcnow()
    if now.astimezone(ZoneInfo(settings.timezone)).day != settings.nps_day_of_month:
        return 0
    already = db.scalar(
        select(Survey.id).where(
            Survey.kind == SurveyKind.NPS, Survey.sent_at >= _month_start_utc(now)
        )
    )
    if already:
        return 0

    other = aliased(Conversation)
    recent_nps = exists().where(
        Survey.contact_id == Contact.id,
        Survey.kind == SurveyKind.NPS,
        Survey.sent_at >= now - timedelta(days=settings.nps_cooldown_days),
    )
    active = exists().where(
        other.contact_id == Contact.id, other.status != ConversationStatus.CLOSED
    )
    last_closed = (
        select(func.max(Conversation.id))
        .where(
            Conversation.contact_id == Contact.id,
            Conversation.status == ConversationStatus.CLOSED,
            Conversation.closed_at >= now - timedelta(days=settings.nps_lookback_days),
        )
        .scalar_subquery()
    )
    rows = db.execute(
        select(Contact.id, last_closed.label("conversation_id"))
        .where(Contact.opt_in_at.is_not(None), ~recent_nps, ~active, last_closed.is_not(None))
        .order_by(func.random())
        .limit(settings.nps_sample_size)
    ).all()

    sent = 0
    for _, conversation_id in rows:
        conversation = db.get(Conversation, conversation_id)
        if _send(db, conversation, SurveyKind.NPS, None).status == SurveyStatus.SENT:
            sent += 1
    db.commit()
    logger.info("nps_sent", extra={"event": "nps_sent", "count": sent})
    return sent
