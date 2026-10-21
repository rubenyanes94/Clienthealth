"""Bot determinista de fase 1: menú → área → escalar a un agente.

Nunca diagnostica ni recomienda medicamentos: solo informa con textos fijos y deriva.
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import utcnow
from app.models import Area, Conversation, FaqEntry
from app.models.enums import ConversationStatus, EventType, SenderType
from app.services import events
from app.services.outbound import send_message

STATE_MENU = "menu"
STATE_FAQ = "faq"
STATE_FAQ_FOLLOWUP = "faq_followup"

HUMAN_KEYWORDS = re.compile(r"\b(agente|asesor|asesora|humano|persona|operador|operadora)\b")

WELCOME = (
    "¡Hola! Gracias por escribir al Centro Médico San Bernardino.\n"
    "Por este canal le ayudamos con información y gestiones. "
    "Si se trata de una emergencia, acuda directamente a nuestra Emergencia."
)
NOT_UNDERSTOOD = "Disculpe, no entendí su respuesta."
FAQ_FOLLOWUP = (
    "¿Le ayudó esta información?\n"
    "1. Sí, era todo\n"
    "2. Quiero hablar con un agente\n"
    "0. Volver al menú"
)
GOODBYE = "¡Gracias por escribirnos! Si necesita algo más, escríbanos cuando quiera."


def active_areas(db: Session) -> list[Area]:
    return list(db.scalars(select(Area).where(Area.is_active).order_by(Area.sort_order, Area.id)))


def active_faqs(db: Session) -> list[FaqEntry]:
    return list(
        db.scalars(
            select(FaqEntry).where(FaqEntry.is_active).order_by(FaqEntry.sort_order, FaqEntry.id)
        )
    )


def default_area(db: Session) -> Area | None:
    areas = active_areas(db)
    return next((a for a in areas if a.is_default), areas[0] if areas else None)


def _menu_text(db: Session) -> str:
    lines = ["Escriba el número de la opción que necesita:"]
    areas = active_areas(db)
    for i, area in enumerate(areas, start=1):
        lines.append(f"{i}. {area.name}")
    if active_faqs(db):
        lines.append(f"{len(areas) + 1}. Preguntas frecuentes")
    return "\n".join(lines)


def _faq_text(db: Session) -> str:
    lines = ["Preguntas frecuentes. Escriba el número:"]
    for i, faq in enumerate(active_faqs(db), start=1):
        lines.append(f"{i}. {faq.title}")
    lines.append("0. Volver al menú")
    return "\n".join(lines)


def _say(db: Session, conversation: Conversation, body: str) -> None:
    message = send_message(db, conversation, body, sender_type=SenderType.BOT)
    events.record(db, conversation, EventType.BOT_MESSAGE, data={"message_id": message.id})


def _parse_choice(text: str) -> int | None:
    match = re.fullmatch(r"\s*(\d{1,2})\s*[.)]?\s*", text)
    return int(match.group(1)) if match else None


def escalate(
    db: Session,
    conversation: Conversation,
    area: Area | None,
    *,
    reason: str,
    notify: bool = True,
) -> None:
    """Saca la conversación del bot y la deja en la cola del área."""
    area = area or default_area(db)
    conversation.area_id = area.id if area else None
    conversation.status = ConversationStatus.QUEUED
    conversation.queued_at = utcnow()
    conversation.bot_state = None
    conversation.bot_invalid_attempts = 0
    events.record(
        db,
        conversation,
        EventType.BOT_ESCALATED,
        data={"area_id": conversation.area_id, "reason": reason},
    )
    if notify:
        area_name = area.name if area else "atención al paciente"
        _say(
            db,
            conversation,
            f"Le estamos comunicando con un agente de {area_name}. "
            "Le responderemos lo antes posible.",
        )


def _resolve(db: Session, conversation: Conversation) -> None:
    _say(db, conversation, GOODBYE)
    now = utcnow()
    conversation.status = ConversationStatus.CLOSED
    conversation.closed_at = now
    conversation.bot_state = None
    events.record(db, conversation, EventType.BOT_RESOLVED)
    events.record(db, conversation, EventType.CLOSED, data={"by": "bot", "reason_id": None})


def _invalid(db: Session, conversation: Conversation, prompt: str) -> None:
    conversation.bot_invalid_attempts += 1
    if conversation.bot_invalid_attempts >= get_settings().bot_max_invalid_attempts:
        escalate(db, conversation, None, reason="invalid_attempts")
        return
    _say(db, conversation, f"{NOT_UNDERSTOOD}\n\n{prompt}")


def _show_menu(db: Session, conversation: Conversation, *, welcome: bool = False) -> None:
    conversation.bot_state = STATE_MENU
    body = _menu_text(db)
    _say(db, conversation, f"{WELCOME}\n\n{body}" if welcome else body)


def handle_inbound(db: Session, conversation: Conversation, text: str) -> None:
    """Avanza la máquina de estados con un mensaje del paciente (status == BOT)."""
    if conversation.status != ConversationStatus.BOT:
        return

    if HUMAN_KEYWORDS.search(text.lower()):
        escalate(db, conversation, None, reason="requested_agent")
        return

    state = conversation.bot_state
    choice = _parse_choice(text)

    if state is None:
        _show_menu(db, conversation, welcome=True)
        return

    if state == STATE_MENU:
        areas = active_areas(db)
        has_faqs = bool(active_faqs(db))
        if choice is not None and 1 <= choice <= len(areas):
            escalate(db, conversation, areas[choice - 1], reason="menu")
        elif has_faqs and choice == len(areas) + 1:
            conversation.bot_state = STATE_FAQ
            conversation.bot_invalid_attempts = 0
            _say(db, conversation, _faq_text(db))
        else:
            _invalid(db, conversation, _menu_text(db))
        return

    if state == STATE_FAQ:
        faqs = active_faqs(db)
        if choice == 0:
            conversation.bot_invalid_attempts = 0
            _show_menu(db, conversation)
        elif choice is not None and 1 <= choice <= len(faqs):
            conversation.bot_state = STATE_FAQ_FOLLOWUP
            conversation.bot_invalid_attempts = 0
            _say(db, conversation, f"{faqs[choice - 1].answer}\n\n{FAQ_FOLLOWUP}")
        else:
            _invalid(db, conversation, _faq_text(db))
        return

    if state == STATE_FAQ_FOLLOWUP:
        if choice == 1:
            _resolve(db, conversation)
        elif choice == 2:
            escalate(db, conversation, None, reason="faq_followup")
        elif choice == 0:
            conversation.bot_invalid_attempts = 0
            _show_menu(db, conversation)
        else:
            _invalid(db, conversation, FAQ_FOLLOWUP)
        return

    # Estado desconocido (p. ej. tras un cambio de versión): volver a empezar.
    _show_menu(db, conversation, welcome=True)
