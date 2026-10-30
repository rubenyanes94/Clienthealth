"""Fichas de pacientes. Nunca se loguean sus datos."""

import re
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.db.base import utcnow
from app.models import Agent, Patient, PatientEvent
from app.models.enums import PatientEventType
from app.services.conversations import ConflictError, NotFoundError

DUPLICATE_ID = "Ya existe un paciente con esa cédula"


def _ensure_id_free(db: Session, national_id: str, except_id: int | None = None) -> None:
    other = db.scalar(select(Patient).where(Patient.national_id == national_id))
    if other is not None and other.id != except_id:
        raise ConflictError(DUPLICATE_ID)


def create(db: Session, agent: Agent, fields: dict[str, Any]) -> Patient:
    _ensure_id_free(db, fields["national_id"])
    patient = Patient(**fields, created_by_agent_id=agent.id)
    db.add(patient)
    try:
        db.flush()
        record(db, patient, PatientEventType.CREATED, agent)
        db.commit()
    except IntegrityError as exc:  # dos registros simultáneos de la misma cédula
        db.rollback()
        raise ConflictError(DUPLICATE_ID) from exc
    return patient


def record(
    db: Session,
    patient: Patient,
    type: PatientEventType,
    agent: Agent,
    data: dict[str, Any] | None = None,
) -> None:
    db.add(PatientEvent(patient_id=patient.id, type=type, agent_id=agent.id, data=data or {}))
    patient.updated_at = utcnow()


def get(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError("Paciente no encontrado")
    return patient


def update(db: Session, agent: Agent, patient_id: int, fields: dict[str, Any]) -> Patient:
    patient = get(db, patient_id)
    if "national_id" in fields:
        _ensure_id_free(db, fields["national_id"], except_id=patient.id)
    changed = [name for name, value in fields.items() if getattr(patient, name) != value]
    if not changed:
        return patient
    for name in changed:
        setattr(patient, name, fields[name])
    record(db, patient, PatientEventType.UPDATED, agent, {"fields": changed})
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(DUPLICATE_ID) from exc
    return patient


def match_query(q: str) -> ColumnElement[bool] | None:
    """Cada palabra debe aparecer en algún dato; un número también se busca como teléfono."""
    words = q.split()
    if not words:
        return None

    def word_match(word: str) -> ColumnElement[bool]:
        compact = re.sub(r"[.\-]", "", word)
        return or_(
            Patient.first_name.icontains(word, autoescape=True),
            Patient.last_name.icontains(word, autoescape=True),
            Patient.email.icontains(word, autoescape=True),
            Patient.national_id.icontains(compact, autoescape=True),
        )

    by_words = and_(*[word_match(w) for w in words])
    digits = re.sub(r"\D", "", q)
    if len(digits) < 4:
        return by_words
    if digits.startswith("0"):
        digits = digits[1:]  # 0414… está guardado como 58414…
    return or_(by_words, Patient.phone.contains(digits, autoescape=True))
