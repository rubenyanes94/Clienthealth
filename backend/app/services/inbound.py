"""Procesamiento del webhook de WhatsApp: guarda primero y después ejecuta urgencia y bot."""

import logging
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import utcnow
from app.models import Contact, Conversation, Message
from app.models.enums import (
    ConversationStatus,
    EventType,
    MessageDirection,
    MessageStatus,
    Priority,
    SenderType,
)
from app.services import bot, events, urgency
from app.services.outbound import send_message

logger = logging.getLogger(__name__)

# Orden de avance de los estados de entrega; "failed" siempre se aplica.
_STATUS_RANK = {
    MessageStatus.SIMULATED: 0,
    MessageStatus.SENT: 1,
    MessageStatus.DELIVERED: 2,
    MessageStatus.READ: 3,
}
_META_STATUSES = {
    "sent": MessageStatus.SENT,
    "delivered": MessageStatus.DELIVERED,
    "read": MessageStatus.READ,
    "failed": MessageStatus.FAILED,
}
_MEDIA_LABELS = {
    "image": "[imagen]",
    "audio": "[audio]",
    "video": "[video]",
    "document": "[documento]",
    "sticker": "[sticker]",
    "location": "[ubicación]",
    "contacts": "[contacto]",
}


def process_payload(db: Session, payload: dict[str, Any]) -> None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            names = {
                c.get("wa_id"): (c.get("profile") or {}).get("name")
                for c in value.get("contacts", [])
            }
            for message in value.get("messages", []):
                handle_inbound_message(db, message, names.get(message.get("from")))
            for status in value.get("statuses", []):
                handle_status(db, status)


def extract_text(message: dict[str, Any]) -> tuple[str, str]:
    """Devuelve (tipo, texto) de un mensaje entrante de Meta."""
    kind = message.get("type", "text")
    if kind == "text":
        return kind, (message.get("text") or {}).get("body", "")
    if kind == "interactive":
        interactive = message.get("interactive") or {}
        reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
        return kind, reply.get("title", "")
    if kind == "button":
        return kind, (message.get("button") or {}).get("text", "")
    return kind, _MEDIA_LABELS.get(kind, f"[{kind}]")


def _get_or_create_contact(db: Session, wa_id: str, name: str | None) -> Contact:
    contact = db.scalar(select(Contact).where(Contact.wa_id == wa_id))
    if contact is None:
        contact = Contact(wa_id=wa_id, name=name)
        db.add(contact)
        db.flush()
    elif name and not contact.name:
        contact.name = name
    return contact


def _find_or_open_conversation(db: Session, contact: Contact) -> Conversation:
    now = utcnow()
    current = db.scalar(
        select(Conversation)
        .where(
            Conversation.contact_id == contact.id,
            Conversation.status != ConversationStatus.CLOSED,
        )
        .order_by(Conversation.id.desc())
        .limit(1)
        .with_for_update()
    )
    if current is not None:
        return current

    last_closed = db.scalar(
        select(Conversation)
        .where(Conversation.contact_id == contact.id)
        .order_by(Conversation.id.desc())
        .limit(1)
        .with_for_update()
    )
    window = timedelta(hours=get_settings().reopen_window_hours)
    if last_closed and last_closed.closed_at and now - last_closed.closed_at < window:
        reopen_by_contact(db, last_closed)
        return last_closed

    conversation = Conversation(
        contact_id=contact.id, status=ConversationStatus.BOT, opened_at=now, updated_at=now
    )
    db.add(conversation)
    db.flush()
    events.record(db, conversation, EventType.CREATED, data={"channel": "whatsapp"})
    return conversation


def reopen_by_contact(db: Session, conversation: Conversation) -> None:
    now = utcnow()
    conversation.closed_at = None
    conversation.assigned_agent_id = None
    if conversation.area_id is None:
        # Lo había resuelto el bot: vuelve a empezar el menú.
        conversation.status = ConversationStatus.BOT
        conversation.bot_state = None
        conversation.bot_invalid_attempts = 0
    else:
        conversation.status = ConversationStatus.QUEUED
        conversation.queued_at = now
    events.record(
        db,
        conversation,
        EventType.REOPENED,
        data={"by": "contact", "status": conversation.status.value},
    )


def handle_inbound_message(db: Session, payload: dict[str, Any], profile_name: str | None) -> None:
    wamid = payload.get("id")
    wa_id = payload.get("from")
    if not wamid or not wa_id:
        return
    if db.scalar(select(Message.id).where(Message.external_id == wamid)) is not None:
        return  # duplicado: Meta reintenta entregas

    kind, text = extract_text(payload)
    now = utcnow()
    try:
        contact = _get_or_create_contact(db, wa_id, profile_name)
        conversation = _find_or_open_conversation(db, contact)
        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.INBOUND,
            sender_type=SenderType.CONTACT,
            message_type=kind,
            body=text,
            external_id=wamid,
            status=MessageStatus.RECEIVED,
            created_at=now,
        )
        db.add(message)
        db.flush()
        conversation.last_inbound_at = now
        conversation.last_message_at = now
        events.record(db, conversation, EventType.INBOUND_MESSAGE, data={"message_id": message.id})

        if conversation.status == ConversationStatus.PENDING:
            conversation.status = ConversationStatus.OPEN
            conversation.pending_since = None
            events.record(db, conversation, EventType.PENDING_RESUMED, data={"by": "contact"})
        db.commit()
    except IntegrityError:
        db.rollback()  # otra instancia procesó el mismo wamid al mismo tiempo
        return

    conversation_id = conversation.id
    try:
        _run_automation(db, conversation, text)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "automation_failed",
            extra={"event": "automation_failed", "conversation_id": conversation_id},
        )
        conversation = db.get(Conversation, conversation_id, with_for_update=True)
        if conversation and conversation.status == ConversationStatus.BOT:
            bot.escalate(db, conversation, None, reason="bot_error", notify=False)
            db.commit()


def _run_automation(db: Session, conversation: Conversation, text: str) -> None:
    """Urgencia primero; si no hay urgencia y la conversación está en el bot, avanza el bot."""
    if urgency.is_urgent(text):
        if not conversation.is_urgent:
            conversation.is_urgent = True
            conversation.priority = Priority.HIGH
            events.record(db, conversation, EventType.URGENCY_DETECTED, data={"source": "rules"})
            message = send_message(
                db, conversation, get_settings().emergency_message, sender_type=SenderType.SYSTEM
            )
            events.record(db, conversation, EventType.BOT_MESSAGE, data={"message_id": message.id})
        if conversation.status == ConversationStatus.BOT:
            bot.escalate(db, conversation, None, reason="urgency", notify=False)
        return

    if conversation.status == ConversationStatus.BOT:
        bot.handle_inbound(db, conversation, text)


def handle_status(db: Session, payload: dict[str, Any]) -> None:
    new_status = _META_STATUSES.get(payload.get("status", ""))
    wamid = payload.get("id")
    if new_status is None or not wamid:
        return
    message = db.scalar(select(Message).where(Message.external_id == wamid).with_for_update())
    if message is None:
        return
    if new_status == MessageStatus.FAILED:
        message.status = new_status
        errors = payload.get("errors") or [{}]
        message.error_code = str(errors[0].get("code", "")) or None
    elif _STATUS_RANK.get(new_status, 0) > _STATUS_RANK.get(message.status, -1):
        message.status = new_status
    else:
        return
    message.conversation.touch()
    db.commit()
