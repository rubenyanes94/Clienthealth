from enum import StrEnum


class AgentRole(StrEnum):
    AGENT = "agent"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"


class ConversationStatus(StrEnum):
    BOT = "bot"  # atendida por el bot, aún sin área
    QUEUED = "queued"  # en cola de un área, sin agente
    OPEN = "open"  # asignada a un agente
    PENDING = "pending"  # esperando al paciente (hitos pausados)
    CLOSED = "closed"


class Priority(StrEnum):
    NORMAL = "normal"
    HIGH = "high"


class MessageDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class SenderType(StrEnum):
    CONTACT = "contact"
    BOT = "bot"
    AGENT = "agent"
    SYSTEM = "system"


class MessageStatus(StrEnum):
    RECEIVED = "received"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    SIMULATED = "simulated"
    NOTE = "note"  # nota interna, nunca sale a WhatsApp


class SurveyKind(StrEnum):
    CSAT = "csat"  # 1–5, al cerrar un caso
    NPS = "nps"  # 0–10, muestreo mensual a contactos con consentimiento


class SurveyStatus(StrEnum):
    SENT = "sent"
    ANSWERED = "answered"
    EXPIRED = "expired"  # el paciente escribió otra cosa o pasó la ventana
    FAILED = "failed"


class EventType(StrEnum):
    CREATED = "created"
    INBOUND_MESSAGE = "inbound_message"
    BOT_MESSAGE = "bot_message"
    BOT_ESCALATED = "bot_escalated"
    BOT_RESOLVED = "bot_resolved"
    URGENCY_DETECTED = "urgency_detected"
    ACCEPTED = "accepted"
    AGENT_MESSAGE = "agent_message"
    INTERNAL_NOTE = "internal_note"
    PENDING_STARTED = "pending_started"
    PENDING_RESUMED = "pending_resumed"
    TRANSFERRED = "transferred"
    CLOSED = "closed"
    REOPENED = "reopened"
    ABANDONED = "abandoned"
    SURVEY_SENT = "survey_sent"
    SURVEY_ANSWERED = "survey_answered"
    CASE_CREATED = "case_created"  # se creó un caso del módulo de Casos desde esta conversación


class CaseStage(StrEnum):
    REGISTERED = "registered"  # en el área, nadie lo atiende todavía
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"  # detenido: esperando al paciente, un resultado u otra persona
    RESOLVED = "resolved"  # solucionado, falta confirmar y cerrar
    CLOSED = "closed"


class PatientEventType(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    CONTACT_LINKED = "contact_linked"


class CaseEventType(StrEnum):
    CREATED = "created"
    STAGE_CHANGED = "stage_changed"
    TRANSFERRED = "transferred"
    TAKEN = "taken"
    UPDATED = "updated"
    NOTE_ADDED = "note_added"
