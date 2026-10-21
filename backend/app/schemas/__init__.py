from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    AgentRole,
    ConversationStatus,
    EventType,
    MessageDirection,
    MessageStatus,
    Priority,
    SenderType,
)


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Auth y catálogos ------------------------------------------------------------------------


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)


class AreaOut(ORM):
    id: int
    name: str
    slug: str
    is_default: bool
    is_active: bool
    sort_order: int
    sla_first_response_minutes: int


class AreaIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 0
    sla_first_response_minutes: int = Field(default=15, ge=1, le=24 * 60)


class AreaPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    is_default: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    sla_first_response_minutes: int | None = Field(default=None, ge=1, le=24 * 60)


class ReasonOut(ORM):
    id: int
    name: str
    area_id: int | None
    is_active: bool


class ReasonIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    area_id: int | None = None
    is_active: bool = True


class ReasonPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    area_id: int | None = None
    is_active: bool | None = None


class FaqOut(ORM):
    id: int
    title: str
    answer: str
    is_active: bool
    sort_order: int


class FaqIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    answer: str = Field(min_length=2, max_length=4000)
    is_active: bool = True
    sort_order: int = 0


class FaqPatch(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    answer: str | None = Field(default=None, min_length=2, max_length=4000)
    is_active: bool | None = None
    sort_order: int | None = None


class AgentOut(ORM):
    id: int
    name: str
    email: str
    role: AgentRole
    area_id: int | None
    is_active: bool
    last_seen_at: datetime | None


class AgentIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=10, max_length=200)
    role: AgentRole = AgentRole.AGENT
    area_id: int | None = None


class AgentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    password: str | None = Field(default=None, min_length=10, max_length=200)
    role: AgentRole | None = None
    area_id: int | None = None
    is_active: bool | None = None


class AgentRef(ORM):
    id: int
    name: str


class AreaRef(ORM):
    id: int
    name: str
    sla_first_response_minutes: int


class ReasonRef(ORM):
    id: int
    name: str


# --- Bandeja y conversaciones ----------------------------------------------------------------


class ContactOut(ORM):
    id: int
    wa_id: str
    name: str | None


class MessageOut(ORM):
    id: int
    direction: MessageDirection
    sender_type: SenderType
    agent: AgentRef | None
    message_type: str
    body: str
    is_internal_note: bool
    status: MessageStatus
    error_code: str | None
    created_at: datetime


class EventOut(ORM):
    id: int
    type: EventType
    agent: AgentRef | None
    area_id: int | None
    data: dict[str, Any]
    created_at: datetime


class ConversationSummary(ORM):
    id: int
    contact: ContactOut
    area: AreaRef | None
    assigned_agent: AgentRef | None
    status: ConversationStatus
    priority: Priority
    is_urgent: bool
    opened_at: datetime
    queued_at: datetime | None
    pending_since: datetime | None
    closed_at: datetime | None
    last_message_at: datetime | None
    last_inbound_at: datetime | None
    updated_at: datetime
    last_message_preview: str | None = None
    last_message_direction: MessageDirection | None = None
    last_message_sender: SenderType | None = None


class ConversationDetail(ConversationSummary):
    contact_reason: ReasonRef | None
    messages: list[MessageOut]
    events: list[EventOut]


class InboxPage(BaseModel):
    items: list[ConversationSummary]
    next_cursor: str | None


class InboxChanges(BaseModel):
    server_time: datetime
    ids: list[int]


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4096)
    is_internal_note: bool = False


class TransferIn(BaseModel):
    area_id: int


class CloseIn(BaseModel):
    contact_reason_id: int


class LiveMetrics(BaseModel):
    queued: int
    urgent_queued: int
    oldest_queued_at: datetime | None
    in_bot: int
    open: int
    pending: int
    agents_online: int


class SimulateInboundIn(BaseModel):
    wa_id: str = Field(default="584140000000", pattern=r"^\d{8,15}$")
    name: str | None = "Paciente de prueba"
    text: str = Field(min_length=1, max_length=4096)


class HealthOut(BaseModel):
    status: str
    database: str
    environment: str
    whatsapp_dry_run: bool
