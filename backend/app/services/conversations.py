"""Acciones de los agentes sobre un caso. Cada cambio de estado registra su evento."""

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.db.base import utcnow
from app.models import Agent, Area, ContactReason, Conversation, Message
from app.models.enums import (
    ConversationStatus,
    EventType,
    MessageDirection,
    MessageStatus,
    SenderType,
)
from app.services import bot, events, whatsapp
from app.services.outbound import send_message

ACTIVE_STATUSES = (ConversationStatus.OPEN, ConversationStatus.PENDING)


class ConversationError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class NotFoundError(ConversationError):
    status_code = 404


class ForbiddenError(ConversationError):
    status_code = 403


class ConflictError(ConversationError):
    status_code = 409


# --- Visibilidad -----------------------------------------------------------------------------


def _area_match(agent: Agent) -> ColumnElement[bool]:
    if agent.area_id is None:
        return Conversation.area_id.is_not(None)
    return Conversation.area_id == agent.area_id


def visibility_filter(agent: Agent) -> ColumnElement[bool] | None:
    """Agentes: la cola de su área y sus casos. Supervisores y admin: todo."""
    if agent.is_supervisor:
        return None
    return or_(
        Conversation.assigned_agent_id == agent.id,
        and_(Conversation.status == ConversationStatus.QUEUED, _area_match(agent)),
    )


def change_feed_filter(agent: Agent) -> ColumnElement[bool] | None:
    """Más amplio que la visibilidad: incluye casos del área tomados por otros, para que la
    bandeja de cada agente se entere de que salieron de la cola. Solo expone IDs."""
    if agent.is_supervisor:
        return None
    return or_(Conversation.assigned_agent_id == agent.id, _area_match(agent))


def can_view(agent: Agent, conversation: Conversation) -> bool:
    if agent.is_supervisor or conversation.assigned_agent_id == agent.id:
        return True
    if conversation.status != ConversationStatus.QUEUED or conversation.area_id is None:
        return False
    return agent.area_id is None or conversation.area_id == agent.area_id


def _can_act(agent: Agent, conversation: Conversation) -> bool:
    return agent.is_supervisor or conversation.assigned_agent_id == agent.id


# --- Carga -----------------------------------------------------------------------------------


def get_visible(db: Session, agent: Agent, conversation_id: int) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or not can_view(agent, conversation):
        raise NotFoundError("Conversación no encontrada")
    return conversation


def _lock(db: Session, agent: Agent, conversation_id: int) -> Conversation:
    """Bloquea la fila (SELECT … FOR UPDATE) para que dos agentes no pisen el mismo caso."""
    conversation = db.get(Conversation, conversation_id, with_for_update=True)
    if conversation is None or not can_view(agent, conversation):
        raise NotFoundError("Conversación no encontrada")
    return conversation


def _require_actor(agent: Agent, conversation: Conversation) -> None:
    if not _can_act(agent, conversation):
        raise ForbiddenError("Solo el agente asignado o un supervisor puede hacer esto")


# --- Acciones --------------------------------------------------------------------------------


def accept(db: Session, agent: Agent, conversation_id: int) -> Conversation:
    conversation = _lock(db, agent, conversation_id)
    previous = conversation.status
    if previous == ConversationStatus.BOT:
        if not agent.is_supervisor:
            raise ForbiddenError("Solo un supervisor puede intervenir una conversación del bot")
        area = bot.default_area(db)
        conversation.area_id = area.id if area else None
        conversation.bot_state = None
    elif previous != ConversationStatus.QUEUED:
        if conversation.assigned_agent_id == agent.id:
            return conversation
        raise ConflictError("Este caso ya fue tomado por otro agente")

    conversation.status = ConversationStatus.OPEN
    conversation.assigned_agent_id = agent.id
    events.record(
        db, conversation, EventType.ACCEPTED, agent=agent, data={"from_status": previous.value}
    )
    db.commit()
    return conversation


def post_message(
    db: Session, agent: Agent, conversation_id: int, body: str, *, is_internal_note: bool
) -> Message:
    conversation = _lock(db, agent, conversation_id)
    body = body.strip()
    if not body:
        raise ConversationError("El mensaje está vacío")

    if is_internal_note:
        if conversation.status == ConversationStatus.BOT and not agent.is_supervisor:
            raise ForbiddenError("No puede anotar en esta conversación")
        message = Message(
            conversation_id=conversation.id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.AGENT,
            agent_id=agent.id,
            body=body,
            is_internal_note=True,
            status=MessageStatus.NOTE,
        )
        db.add(message)
        db.flush()
        conversation.touch()
        events.record(
            db, conversation, EventType.INTERNAL_NOTE, agent=agent, data={"message_id": message.id}
        )
        db.commit()
        return message

    if conversation.status not in ACTIVE_STATUSES:
        raise ConflictError("Acepte el caso antes de responder")
    _require_actor(agent, conversation)
    if not whatsapp.within_service_window(conversation.last_inbound_at, utcnow()):
        raise ConflictError(
            "Pasaron más de 24 h desde el último mensaje del paciente: "
            "solo se pueden enviar plantillas aprobadas"
        )

    message = send_message(db, conversation, body, sender_type=SenderType.AGENT, agent=agent)
    events.record(
        db,
        conversation,
        EventType.AGENT_MESSAGE,
        agent=agent,
        data={"message_id": message.id, "status": message.status.value},
    )
    db.commit()
    return message


def set_pending(db: Session, agent: Agent, conversation_id: int) -> Conversation:
    conversation = _lock(db, agent, conversation_id)
    _require_actor(agent, conversation)
    if conversation.status != ConversationStatus.OPEN:
        raise ConflictError("Solo un caso abierto puede pasar a en espera")
    conversation.status = ConversationStatus.PENDING
    conversation.pending_since = utcnow()
    events.record(db, conversation, EventType.PENDING_STARTED, agent=agent)
    db.commit()
    return conversation


def resume(db: Session, agent: Agent, conversation_id: int) -> Conversation:
    conversation = _lock(db, agent, conversation_id)
    _require_actor(agent, conversation)
    if conversation.status != ConversationStatus.PENDING:
        raise ConflictError("El caso no está en espera")
    conversation.status = ConversationStatus.OPEN
    conversation.pending_since = None
    events.record(db, conversation, EventType.PENDING_RESUMED, agent=agent, data={"by": "agent"})
    db.commit()
    return conversation


def transfer(db: Session, agent: Agent, conversation_id: int, area_id: int) -> Conversation:
    conversation = _lock(db, agent, conversation_id)
    if conversation.status not in (*ACTIVE_STATUSES, ConversationStatus.QUEUED):
        raise ConflictError("No se puede transferir este caso")
    if conversation.status != ConversationStatus.QUEUED:
        _require_actor(agent, conversation)
    area = db.get(Area, area_id)
    if area is None or not area.is_active:
        raise ConversationError("Área no válida")
    if area.id == conversation.area_id:
        raise ConversationError("El caso ya está en esa área")

    from_area_id = conversation.area_id
    conversation.area_id = area.id
    conversation.status = ConversationStatus.QUEUED
    conversation.assigned_agent_id = None
    conversation.pending_since = None
    conversation.queued_at = utcnow()
    events.record(
        db,
        conversation,
        EventType.TRANSFERRED,
        agent=agent,
        data={"from_area_id": from_area_id, "to_area_id": area.id},
    )
    db.commit()
    return conversation


def close(db: Session, agent: Agent, conversation_id: int, contact_reason_id: int) -> Conversation:
    conversation = _lock(db, agent, conversation_id)
    if conversation.status == ConversationStatus.CLOSED:
        raise ConflictError("El caso ya está cerrado")
    _require_actor(agent, conversation)
    reason = db.get(ContactReason, contact_reason_id)
    if reason is None or not reason.is_active:
        raise ConversationError("Motivo de contacto no válido")

    conversation.status = ConversationStatus.CLOSED
    conversation.contact_reason_id = reason.id
    conversation.closed_at = utcnow()
    conversation.pending_since = None
    conversation.bot_state = None
    events.record(
        db,
        conversation,
        EventType.CLOSED,
        agent=agent,
        data={"by": "agent", "reason_id": reason.id},
    )
    db.commit()
    return conversation


def reopen(db: Session, agent: Agent, conversation_id: int) -> Conversation:
    conversation = db.get(Conversation, conversation_id, with_for_update=True)
    if conversation is None or not (
        agent.is_supervisor or conversation.assigned_agent_id == agent.id
    ):
        raise NotFoundError("Conversación no encontrada")
    if conversation.status != ConversationStatus.CLOSED:
        raise ConflictError("El caso no está cerrado")
    if conversation.area_id is None:
        area = bot.default_area(db)
        conversation.area_id = area.id if area else None
    conversation.status = ConversationStatus.OPEN
    conversation.assigned_agent_id = agent.id
    conversation.closed_at = None
    events.record(
        db, conversation, EventType.REOPENED, agent=agent, data={"by": "agent", "status": "open"}
    )
    db.commit()
    return conversation


def list_filter(agent: Agent, name: str) -> list[ColumnElement[bool]]:
    """Condiciones SQL de cada pestaña de la bandeja."""
    clauses: list[ColumnElement[bool]] = []
    visibility = visibility_filter(agent)
    if visibility is not None:
        clauses.append(visibility)
    match name:
        case "open":
            statuses = [ConversationStatus.QUEUED, *ACTIVE_STATUSES]
            if agent.is_supervisor:
                statuses.append(ConversationStatus.BOT)
            clauses.append(Conversation.status.in_(statuses))
        case "queue":
            clauses.append(Conversation.status == ConversationStatus.QUEUED)
        case "mine":
            clauses.append(Conversation.assigned_agent_id == agent.id)
            clauses.append(Conversation.status.in_(ACTIVE_STATUSES))
        case "pending":
            clauses.append(Conversation.status == ConversationStatus.PENDING)
        case "closed":
            clauses.append(Conversation.status == ConversationStatus.CLOSED)
        case "bot":
            clauses.append(
                Conversation.status == ConversationStatus.BOT if agent.is_supervisor else false()
            )
        case "all":
            pass
        case _:
            raise ConversationError("Filtro no válido")
    return clauses


def latest_messages(db: Session, conversation_ids: list[int]) -> dict[int, Message]:
    if not conversation_ids:
        return {}

    last_ids = (
        select(func.max(Message.id))
        .where(Message.conversation_id.in_(conversation_ids), Message.is_internal_note.is_(False))
        .group_by(Message.conversation_id)
    )
    rows = db.scalars(select(Message).where(Message.id.in_(last_ids)))
    return {m.conversation_id: m for m in rows}
