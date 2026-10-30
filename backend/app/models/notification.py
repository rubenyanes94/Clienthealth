from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, utcnow
from app.models.case import Case, CaseTask
from app.models.enums import NotificationType
from app.models.org import Agent, enum_col


class Notification(Base):
    """Aviso para una persona. No guarda texto: el título y el cuerpo se arman al mostrarlo, con el
    caso y la tarea a los que apunta, para que nunca queden copias de datos del paciente."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_recipient", "recipient_agent_id", "read_at", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"))
    actor_agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    type: Mapped[NotificationType] = mapped_column(enum_col(NotificationType, "notification_type"))
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("case_tasks.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    actor: Mapped[Agent | None] = relationship(foreign_keys=[actor_agent_id])
    case: Mapped[Case] = relationship()
    task: Mapped[CaseTask | None] = relationship()
