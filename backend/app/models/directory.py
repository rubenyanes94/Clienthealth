from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, UTCDateTime, utcnow
from app.models.org import Agent


class DirectoryDoctor(Base):
    """Un médico del directorio, importado de la web del centro e interpretado.

    No es personal de la consola: es información pública para orientar al paciente.
    """

    __tablename__ = "directory_doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(Integer, unique=True)  # id de la entrada en WordPress
    source_url: Mapped[str] = mapped_column(String(500))
    source_modified: Mapped[str | None] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))  # «Apellidos, Nombres», como en la web
    display_name: Mapped[str] = mapped_column(String(200))
    specialties: Mapped[list[str]] = mapped_column(JSONType, default=list)
    specialty_text: Mapped[str | None] = mapped_column(Text)
    offices: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)
    schedule: Mapped[list[str]] = mapped_column(JSONType, default=list)
    by_appointment: Mapped[bool] = mapped_column(Boolean, default=False)
    phones: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list)
    emails: Mapped[list[str]] = mapped_column(JSONType, default=list)
    raw_lines: Mapped[list[str]] = mapped_column(JSONType, default=list)
    review_notes: Mapped[list[str]] = mapped_column(JSONType, default=list)
    search_text: Mapped[str] = mapped_column(Text, default="")
    fingerprint: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # falso si ya no está en la web
    imported_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class DirectoryImport(Base):
    """Cada actualización aplicada: quién, cuándo y qué cambió."""

    __tablename__ = "directory_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[int | None] = mapped_column(ForeignKey("agents.id"))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    total: Mapped[int] = mapped_column(Integer)
    created: Mapped[int] = mapped_column(Integer)
    updated: Mapped[int] = mapped_column(Integer)
    removed: Mapped[int] = mapped_column(Integer)
    needs_review: Mapped[int] = mapped_column(Integer)

    agent: Mapped[Agent | None] = relationship()
