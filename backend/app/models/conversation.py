from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, UTCDateTime, utcnow
from app.models.enums import (
    ConversationStatus,
    EventType,
    MessageDirection,
    MessageStatus,
    Priority,
    SenderType,
)
from app.models.org import Agent, Area, ContactReason, enum_col


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    wa_id: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str | None] = mapped_column(String(255))
    opt_in_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_status_updated", "status", "updated_at"),
        Index("ix_conversations_contact_status", "contact_id", "status"),
        Index("ix_conversations_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"))
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    contact_reason_id: Mapped[int | None] = mapped_column(ForeignKey("contact_reasons.id"))

    status: Mapped[ConversationStatus] = mapped_column(
        enum_col(ConversationStatus, "conversation_status"), default=ConversationStatus.BOT
    )
    priority: Mapped[Priority] = mapped_column(
        enum_col(Priority, "priority"), default=Priority.NORMAL
    )
    is_urgent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Estado de la máquina del bot (solo mientras status == BOT)
    bot_state: Mapped[str | None] = mapped_column(String(40))
    bot_invalid_attempts: Mapped[int] = mapped_column(Integer, default=0)

    opened_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    queued_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    pending_since: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_message_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    last_inbound_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    contact: Mapped[Contact] = relationship()
    area: Mapped[Area | None] = relationship()
    assigned_agent: Mapped[Agent | None] = relationship()
    contact_reason: Mapped[ContactReason | None] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", order_by="Message.id"
    )
    events: Mapped[list["ConversationEvent"]] = relationship(order_by="ConversationEvent.id")

    def touch(self) -> None:
        """Marca un cambio para que el polling de /inbox/changes lo detecte."""
        self.updated_at = utcnow()


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_id_id", "conversation_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    direction: Mapped[MessageDirection] = mapped_column(
        enum_col(MessageDirection, "message_direction")
    )
    sender_type: Mapped[SenderType] = mapped_column(enum_col(SenderType, "sender_type"))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    message_type: Mapped[str] = mapped_column(String(30), default="text")
    body: Mapped[str] = mapped_column(Text, default="")
    is_internal_note: Mapped[bool] = mapped_column(Boolean, default=False)
    # wamid de Meta: garantiza la idempotencia del webhook
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    status: Mapped[MessageStatus] = mapped_column(enum_col(MessageStatus, "message_status"))
    error_code: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    agent: Mapped[Agent | None] = relationship()


class ConversationEvent(Base):
    """Registro inmutable. Todas las métricas se calculan desde aquí.

    `data` nunca contiene texto del paciente: solo IDs, estados y números.
    """

    __tablename__ = "conversation_events"
    __table_args__ = (
        Index("ix_conversation_events_conversation_created", "conversation_id", "created_at"),
        Index("ix_conversation_events_type_created", "type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    type: Mapped[EventType] = mapped_column(enum_col(EventType, "event_type"))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    agent: Mapped[Agent | None] = relationship()
