from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, UTCDateTime, utcnow
from app.models.conversation import Contact, Conversation
from app.models.enums import CaseEventType, CaseStage, PatientEventType, Priority
from app.models.org import Agent, Area, ContactReason, enum_col


class Patient(Base):
    """Ficha del paciente. Independiente de WhatsApp: puede llegar en persona a la sala."""

    __tablename__ = "patients"
    __table_args__ = (Index("ix_patients_last_first", "last_name", "first_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    # Sin puntos ni guiones (V12345678), para que no se repita escrita de otra forma.
    national_id: Mapped[str] = mapped_column(String(20), unique=True)
    # Solo dígitos, con código de país, igual que Contact.wa_id.
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255))
    # Número de WhatsApp con el que escribe, si ya se creó un caso desde una conversación.
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), unique=True)
    created_by_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    contact: Mapped[Contact | None] = relationship()
    events: Mapped[list["PatientEvent"]] = relationship(order_by="PatientEvent.id")


class PatientEvent(Base):
    """Quién registró o cambió cada ficha. `data` guarda nombres de campos, nunca sus valores."""

    __tablename__ = "patient_events"
    __table_args__ = (Index("ix_patient_events_patient", "patient_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    type: Mapped[PatientEventType] = mapped_column(enum_col(PatientEventType, "patient_event_type"))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    agent: Mapped[Agent | None] = relationship()


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        Index("ix_cases_stage_changed", "stage", "stage_changed_at"),
        Index("ix_cases_area_stage", "area_id", "stage"),
        Index("ix_cases_patient", "patient_id"),
        Index("ix_cases_conversation", "conversation_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    assigned_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    contact_reason_id: Mapped[int | None] = mapped_column(ForeignKey("contact_reasons.id"))
    # Presente si el caso se creó desde el módulo de Conversaciones.
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id"))
    created_by_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))

    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[CaseStage] = mapped_column(
        enum_col(CaseStage, "case_stage"), default=CaseStage.REGISTERED
    )
    priority: Mapped[Priority] = mapped_column(
        enum_col(Priority, "priority"), default=Priority.NORMAL
    )

    opened_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    # Desde cuándo está en esta etapa y área: alimenta los contadores de la sala.
    stage_changed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    patient: Mapped[Patient] = relationship()
    area: Mapped[Area] = relationship()
    assigned_agent: Mapped[Agent | None] = relationship(foreign_keys=[assigned_agent_id])
    created_by: Mapped[Agent | None] = relationship(foreign_keys=[created_by_agent_id])
    contact_reason: Mapped[ContactReason | None] = relationship()
    conversation: Mapped[Conversation | None] = relationship()
    events: Mapped[list["CaseEvent"]] = relationship(order_by="CaseEvent.id")
    notes: Mapped[list["CaseNote"]] = relationship(order_by="CaseNote.id")


class CaseEvent(Base):
    """Registro inmutable de un caso. Los indicadores de la sala se calculan desde aquí.

    `data` nunca contiene texto del paciente: solo IDs, etapas y nombres de campos.
    """

    __tablename__ = "case_events"
    __table_args__ = (
        Index("ix_case_events_case_created", "case_id", "created_at"),
        Index("ix_case_events_type_created", "type", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    type: Mapped[CaseEventType] = mapped_column(enum_col(CaseEventType, "case_event_type"))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))
    data: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    agent: Mapped[Agent | None] = relationship()


class CaseNote(Base):
    """Nota del equipo sobre un caso. El texto vive aquí y nunca en `CaseEvent.data`."""

    __tablename__ = "case_notes"
    __table_args__ = (Index("ix_case_notes_case", "case_id", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    agent: Mapped[Agent | None] = relationship()
