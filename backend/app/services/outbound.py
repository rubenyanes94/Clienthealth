from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import Agent, Conversation, Message
from app.models.enums import MessageDirection, SenderType
from app.services import whatsapp


def send_message(
    db: Session,
    conversation: Conversation,
    body: str,
    *,
    sender_type: SenderType,
    agent: Agent | None = None,
) -> Message:
    """Envía texto libre (dentro de la ventana de 24 h, que valida quien llama) y lo guarda."""
    result = whatsapp.send_text(conversation.contact.wa_id, body)
    return _store(db, conversation, body, result, sender_type=sender_type, agent=agent)


def send_template(db: Session, conversation: Conversation, template: str, preview: str) -> Message:
    """Envía una plantilla aprobada; `preview` es el texto que ve el agente en el chat."""
    result = whatsapp.send_template(conversation.contact.wa_id, template)
    message = _store(db, conversation, preview, result, sender_type=SenderType.SYSTEM)
    message.message_type = "template"
    return message


def _store(
    db: Session,
    conversation: Conversation,
    body: str,
    result: whatsapp.SendResult,
    *,
    sender_type: SenderType,
    agent: Agent | None = None,
) -> Message:
    now = utcnow()
    message = Message(
        conversation_id=conversation.id,
        direction=MessageDirection.OUTBOUND,
        sender_type=sender_type,
        agent_id=agent.id if agent else None,
        body=body,
        external_id=result.external_id,
        status=result.status,
        error_code=result.error_code,
        created_at=now,
    )
    db.add(message)
    conversation.last_message_at = now
    conversation.touch()
    db.flush()
    return message
