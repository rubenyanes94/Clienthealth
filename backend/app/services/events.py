from typing import Any

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import Agent, Case, CaseEvent, Conversation, ConversationEvent
from app.models.enums import CaseEventType, EventType


def record(
    db: Session,
    conversation: Conversation,
    type: EventType,
    *,
    agent: Agent | None = None,
    data: dict[str, Any] | None = None,
) -> ConversationEvent:
    """Registra un evento en la misma transacción que el cambio de estado.

    `data` solo admite IDs, estados y números. Nunca texto del paciente.
    """
    now = utcnow()
    event = ConversationEvent(
        conversation_id=conversation.id,
        type=type,
        agent_id=agent.id if agent else None,
        area_id=conversation.area_id,
        data=data or {},
        created_at=now,
    )
    db.add(event)
    conversation.updated_at = now
    return event


def record_case(
    db: Session,
    case: Case,
    type: CaseEventType,
    *,
    agent: Agent | None = None,
    data: dict[str, Any] | None = None,
) -> CaseEvent:
    """Igual que `record`, para los casos. `data` tampoco admite texto del paciente."""
    now = utcnow()
    event = CaseEvent(
        case_id=case.id,
        type=type,
        agent_id=agent.id if agent else None,
        area_id=case.area_id,
        data=data or {},
        created_at=now,
    )
    db.add(event)
    case.updated_at = now
    return event
