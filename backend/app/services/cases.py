"""Módulo de Casos: gestión entre áreas. Cada cambio registra su evento en la misma transacción."""

from datetime import datetime, time, timedelta
from statistics import median
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import get_settings
from app.db.base import utcnow
from app.models import Agent, Area, Case, CaseEvent, CaseNote, ContactReason, Patient
from app.models.enums import CaseEventType, CaseStage, EventType, PatientEventType, Priority
from app.services import conversations, events, patients
from app.services.conversations import ConflictError, ConversationError, NotFoundError

# Pasos permitidos. Un caso resuelto puede volver a atención si el problema sigue, y uno cerrado
# se reabre en atención.
NEXT_STAGES: dict[CaseStage, tuple[CaseStage, ...]] = {
    CaseStage.REGISTERED: (CaseStage.IN_PROGRESS,),
    CaseStage.IN_PROGRESS: (CaseStage.RESOLVED, CaseStage.WAITING),
    CaseStage.WAITING: (CaseStage.IN_PROGRESS,),
    CaseStage.RESOLVED: (CaseStage.CLOSED, CaseStage.IN_PROGRESS),
    CaseStage.CLOSED: (CaseStage.IN_PROGRESS,),
}
TRANSFERABLE = (CaseStage.REGISTERED, CaseStage.IN_PROGRESS, CaseStage.WAITING)
LIVE_STAGES = (
    CaseStage.REGISTERED,
    CaseStage.IN_PROGRESS,
    CaseStage.WAITING,
    CaseStage.RESOLVED,
)


def _active_area(db: Session, area_id: int) -> Area:
    area = db.get(Area, area_id)
    if area is None or not area.is_active:
        raise ConversationError("Área no válida")
    return area


def _lock(db: Session, case_id: int) -> Case:
    """Bloquea la fila: dos tabletas no pueden mover el mismo caso a la vez."""
    case = db.get(Case, case_id, with_for_update=True)
    if case is None:
        raise NotFoundError("Caso no encontrado")
    return case


def get(db: Session, case_id: int) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise NotFoundError("Caso no encontrado")
    return case


def create(
    db: Session,
    agent: Agent,
    *,
    patient_id: int,
    area_id: int,
    subject: str,
    description: str,
    priority: Priority,
    conversation_id: int | None,
) -> Case:
    patient = patients.get(db, patient_id)
    area = _active_area(db, area_id)
    conversation = None
    if conversation_id is not None:
        conversation = conversations.get_visible(db, agent, conversation_id)

    now = utcnow()
    case = Case(
        patient_id=patient.id,
        area_id=area.id,
        conversation_id=conversation.id if conversation else None,
        created_by_agent_id=agent.id,
        subject=subject.strip(),
        description=description.strip(),
        priority=priority,
        stage=CaseStage.REGISTERED,
        opened_at=now,
        stage_changed_at=now,
        updated_at=now,
    )
    db.add(case)
    db.flush()
    events.record_case(db, case, CaseEventType.CREATED, agent=agent, data={"area_id": area.id})
    if conversation is not None:
        _link_contact(db, agent, patient, conversation.contact_id)
        events.record(
            db, conversation, EventType.CASE_CREATED, agent=agent, data={"case_id": case.id}
        )
    db.commit()
    return case


def _link_contact(db: Session, agent: Agent, patient: Patient, contact_id: int) -> None:
    """Recuerda el WhatsApp del paciente. Un número ya vinculado no se reasigna: una madre puede
    escribir por varios hijos."""
    taken = db.scalar(select(Patient.id).where(Patient.contact_id == contact_id))
    if patient.contact_id is None and taken is None:
        patient.contact_id = contact_id
        patients.record(db, patient, PatientEventType.CONTACT_LINKED, agent)


def update(db: Session, agent: Agent, case_id: int, fields: dict[str, Any]) -> Case:
    case = _lock(db, case_id)
    if case.stage == CaseStage.CLOSED:
        raise ConflictError("Reabra el caso para modificarlo")
    changed = [name for name, value in fields.items() if getattr(case, name) != value]
    if changed:
        for name in changed:
            setattr(case, name, fields[name])
        events.record_case(db, case, CaseEventType.UPDATED, agent=agent, data={"fields": changed})
    db.commit()
    return case


def change_stage(
    db: Session, agent: Agent, case_id: int, stage: CaseStage, contact_reason_id: int | None
) -> Case:
    case = _lock(db, case_id)
    previous = case.stage
    if stage not in NEXT_STAGES[previous]:
        # Lo normal es que otra tableta se haya adelantado.
        raise ConflictError("El caso cambió de etapa: revise su estado actual")

    now = utcnow()
    if stage == CaseStage.CLOSED:
        _set_close_reason(db, case, contact_reason_id)
        case.closed_at = now
    if stage == CaseStage.RESOLVED:
        case.resolved_at = now
    if stage == CaseStage.IN_PROGRESS:
        case.closed_at = None
        case.resolved_at = None
        if case.assigned_agent_id is None:
            case.assigned_agent_id = agent.id

    case.stage = stage
    case.stage_changed_at = now
    events.record_case(
        db,
        case,
        CaseEventType.STAGE_CHANGED,
        agent=agent,
        data={"from": previous.value, "to": stage.value},
    )
    db.commit()
    return case


def _set_close_reason(db: Session, case: Case, contact_reason_id: int | None) -> None:
    if contact_reason_id is None:
        if case.contact_reason_id is None:
            raise ConversationError("Indique el motivo para cerrar el caso")
        return
    reason = db.get(ContactReason, contact_reason_id)
    if reason is None or not reason.is_active:
        raise ConversationError("Motivo de contacto no válido")
    case.contact_reason_id = reason.id


def transfer(db: Session, agent: Agent, case_id: int, area_id: int) -> Case:
    """El caso entra por atender en la otra área, que debe tomarlo."""
    case = _lock(db, case_id)
    if case.stage not in TRANSFERABLE:
        raise ConflictError("No se puede transferir un caso resuelto o cerrado")
    area = _active_area(db, area_id)
    if area.id == case.area_id:
        raise ConversationError("El caso ya está en esa área")

    data = {"from_area_id": case.area_id, "to_area_id": area.id, "from_stage": case.stage.value}
    case.area_id = area.id
    case.assigned_agent_id = None
    case.stage = CaseStage.REGISTERED
    case.stage_changed_at = utcnow()
    events.record_case(db, case, CaseEventType.TRANSFERRED, agent=agent, data=data)
    db.commit()
    return case


def take(db: Session, agent: Agent, case_id: int) -> Case:
    case = _lock(db, case_id)
    if case.stage == CaseStage.CLOSED:
        raise ConflictError("Reabra el caso para tomarlo")
    if case.assigned_agent_id == agent.id:
        return case
    previous = case.assigned_agent_id
    case.assigned_agent_id = agent.id
    events.record_case(db, case, CaseEventType.TAKEN, agent=agent, data={"from_agent_id": previous})
    db.commit()
    return case


def add_note(db: Session, agent: Agent, case_id: int, body: str) -> CaseNote:
    case = _lock(db, case_id)
    body = body.strip()
    if not body:
        raise ConversationError("La nota está vacía")
    note = CaseNote(case_id=case.id, agent_id=agent.id, body=body)
    db.add(note)
    db.flush()
    events.record_case(db, case, CaseEventType.NOTE_ADDED, agent=agent, data={"note_id": note.id})
    db.commit()
    return note


# --- Listado ---------------------------------------------------------------------------------


def search_filters(
    agent: Agent, *, stage: str, area_id: int | None, mine: bool, q: str
) -> list[ColumnElement[bool]]:
    clauses: list[ColumnElement[bool]] = []
    if stage == "open":
        clauses.append(Case.stage != CaseStage.CLOSED)
    elif stage != "all":
        clauses.append(Case.stage == CaseStage(stage))
    if area_id is not None:
        clauses.append(Case.area_id == area_id)
    if mine:
        clauses.append(Case.assigned_agent_id == agent.id)
    if q.strip():
        text = q.strip()
        options: list[ColumnElement[bool]] = [Case.subject.icontains(text, autoescape=True)]
        if (by_patient := patients.match_query(text)) is not None:
            options.append(by_patient)
        if text.lstrip("#").isdigit() and len(text) < 10:
            options.append(Case.id == int(text.lstrip("#")))
        clauses.append(or_(*options))
    return clauses


# --- Sala en tiempo real (definiciones en docs/METRICAS.md) -----------------------------------


def waiting_minutes(events_: list[CaseEvent], until: datetime) -> float:
    """Minutos que el caso pasó en espera hasta `until`."""
    total = 0.0
    since: datetime | None = None
    for event in events_:
        if event.created_at > until:
            break
        if event.type == CaseEventType.STAGE_CHANGED and event.data.get("to") == "waiting":
            since = event.created_at
        elif since is not None and event.type in (
            CaseEventType.STAGE_CHANGED,
            CaseEventType.TRANSFERRED,
        ):
            total += (event.created_at - since).total_seconds() / 60
            since = None
    if since is not None:
        total += (until - since).total_seconds() / 60
    return total


def first_attention_minutes(opened_at: datetime, events_: list[CaseEvent]) -> float | None:
    for event in events_:
        if event.type == CaseEventType.STAGE_CHANGED and event.data.get("to") == "in_progress":
            return (event.created_at - opened_at).total_seconds() / 60
    return None


def resolution_minutes(case: Case, events_: list[CaseEvent]) -> float | None:
    if case.resolved_at is None:
        return None
    elapsed = (case.resolved_at - case.opened_at).total_seconds() / 60
    return elapsed - waiting_minutes(events_, case.resolved_at)


def _start_of_today(now: datetime) -> datetime:
    tz = ZoneInfo(get_settings().timezone)
    return datetime.combine(now.astimezone(tz).date(), time.min, tzinfo=tz)


def _median(values: list[float]) -> float | None:
    return round(median(values), 1) if values else None


def live(db: Session, now: datetime) -> dict[str, Any]:
    def blank() -> dict[str, Any]:
        return {
            "registered": 0,
            "in_progress": 0,
            "waiting": 0,
            "resolved": 0,
            "late": 0,
            "oldest_registered_at": None,
        }

    goal = timedelta(minutes=get_settings().case_goal_minutes)

    def count(bucket: dict[str, Any], case: Case) -> None:
        bucket[case.stage.value] += 1
        if case.stage != CaseStage.REGISTERED:
            return
        if (now - case.stage_changed_at) >= goal:
            bucket["late"] += 1
        oldest = bucket["oldest_registered_at"]
        if oldest is None or case.stage_changed_at < oldest:
            bucket["oldest_registered_at"] = case.stage_changed_at

    areas = {a.id: a for a in db.scalars(select(Area).order_by(Area.sort_order, Area.name))}
    per_area = {a.id: blank() for a in areas.values() if a.is_active}
    totals = blank()
    urgent = 0
    for case in db.scalars(select(Case).where(Case.stage.in_(LIVE_STAGES))):
        count(totals, case)
        count(per_area.setdefault(case.area_id, blank()), case)
        urgent += case.priority == Priority.HIGH

    today = _start_of_today(now)
    recent = list(
        db.scalars(select(Case).where(or_(Case.opened_at >= today, Case.resolved_at >= today)))
    )
    by_case: dict[int, list[CaseEvent]] = {}
    if recent:
        rows = db.scalars(
            select(CaseEvent)
            .where(CaseEvent.case_id.in_([c.id for c in recent]))
            .order_by(CaseEvent.id)
        )
        for event in rows:
            by_case.setdefault(event.case_id, []).append(event)

    first_attention = [
        minutes
        for c in recent
        if c.opened_at >= today
        and (minutes := first_attention_minutes(c.opened_at, by_case.get(c.id, []))) is not None
    ]
    resolution = [
        minutes
        for c in recent
        if c.resolved_at is not None
        and c.resolved_at >= today
        and (minutes := resolution_minutes(c, by_case.get(c.id, []))) is not None
    ]
    closed_today = db.scalar(select(func.count()).select_from(Case).where(Case.closed_at >= today))
    return {
        **totals,
        "urgent": urgent,
        "goal_minutes": get_settings().case_goal_minutes,
        "created_today": sum(c.opened_at >= today for c in recent),
        "closed_today": closed_today or 0,
        "first_attention_median": _median(first_attention),
        "resolution_median": _median(resolution),
        "areas": [{**bucket, "area": areas[area_id]} for area_id, bucket in per_area.items()],
    }
