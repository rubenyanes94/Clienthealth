from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_agent, require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models import Agent, Area, BusinessHours, ContactReason, FaqEntry, Holiday
from app.models.enums import AgentRole
from app.schemas import (
    AgentIn,
    AgentOut,
    AgentPatch,
    AreaIn,
    AreaOut,
    AreaPatch,
    FaqIn,
    FaqOut,
    FaqPatch,
    ReasonIn,
    ReasonOut,
    ReasonPatch,
)
from app.schemas.metrics import HolidayIn, HolidayOut, ScheduleIn, ScheduleOut, Slot

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])


class Catalog(BaseModel):
    areas: list[AreaOut]
    reasons: list[ReasonOut]


@catalog_router.get("", response_model=Catalog)
def catalog(_: Agent = Depends(current_agent), db: Session = Depends(get_db)) -> Catalog:
    """Áreas y motivos activos, para transferir y cerrar casos."""
    areas = db.scalars(select(Area).where(Area.is_active).order_by(Area.sort_order, Area.id))
    reasons = db.scalars(
        select(ContactReason).where(ContactReason.is_active).order_by(ContactReason.name)
    )
    return Catalog(
        areas=[AreaOut.model_validate(a) for a in areas],
        reasons=[ReasonOut.model_validate(r) for r in reasons],
    )


def _save(db: Session, obj: Any, before_commit: Callable[[], None] | None = None) -> Any:
    try:
        db.flush()
        if before_commit:
            before_commit()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un registro con esos datos"
        ) from exc
    db.refresh(obj)
    return obj


def _get(db: Session, model: type, obj_id: int) -> Any:
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado")
    return obj


def _apply(obj: Any, patch: BaseModel) -> None:
    for key, value in patch.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)


def _single_default(db: Session, area: Area) -> None:
    if area.is_default:
        db.execute(update(Area).where(Area.id != area.id).values(is_default=False))


# --- Áreas -----------------------------------------------------------------------------------


@router.get("/areas", response_model=list[AreaOut])
def list_areas(db: Session = Depends(get_db)):
    return db.scalars(select(Area).order_by(Area.sort_order, Area.id)).all()


@router.post("/areas", response_model=AreaOut, status_code=201)
def create_area(body: AreaIn, db: Session = Depends(get_db)):
    area = Area(**body.model_dump())
    db.add(area)
    return _save(db, area, lambda: _single_default(db, area))


@router.patch("/areas/{area_id}", response_model=AreaOut)
def patch_area(area_id: int, body: AreaPatch, db: Session = Depends(get_db)):
    area = _get(db, Area, area_id)
    _apply(area, body)
    return _save(db, area, lambda: _single_default(db, area))


# --- Motivos ---------------------------------------------------------------------------------


@router.get("/reasons", response_model=list[ReasonOut])
def list_reasons(db: Session = Depends(get_db)):
    return db.scalars(select(ContactReason).order_by(ContactReason.name)).all()


@router.post("/reasons", response_model=ReasonOut, status_code=201)
def create_reason(body: ReasonIn, db: Session = Depends(get_db)):
    reason = ContactReason(**body.model_dump())
    db.add(reason)
    return _save(db, reason)


@router.patch("/reasons/{reason_id}", response_model=ReasonOut)
def patch_reason(reason_id: int, body: ReasonPatch, db: Session = Depends(get_db)):
    reason = _get(db, ContactReason, reason_id)
    _apply(reason, body)
    return _save(db, reason)


# --- Preguntas frecuentes del bot ------------------------------------------------------------


@router.get("/faqs", response_model=list[FaqOut])
def list_faqs(db: Session = Depends(get_db)):
    return db.scalars(select(FaqEntry).order_by(FaqEntry.sort_order, FaqEntry.id)).all()


@router.post("/faqs", response_model=FaqOut, status_code=201)
def create_faq(body: FaqIn, db: Session = Depends(get_db)):
    faq = FaqEntry(**body.model_dump())
    db.add(faq)
    return _save(db, faq)


@router.patch("/faqs/{faq_id}", response_model=FaqOut)
def patch_faq(faq_id: int, body: FaqPatch, db: Session = Depends(get_db)):
    faq = _get(db, FaqEntry, faq_id)
    _apply(faq, body)
    return _save(db, faq)


# --- Agentes ---------------------------------------------------------------------------------


@router.get("/agents", response_model=list[AgentOut])
def list_agents(db: Session = Depends(get_db)):
    return db.scalars(select(Agent).order_by(Agent.name)).all()


@router.post("/agents", response_model=AgentOut, status_code=201)
def create_agent(body: AgentIn, db: Session = Depends(get_db)):
    data = body.model_dump(exclude={"password"})
    data["email"] = data["email"].lower()
    agent = Agent(**data, password_hash=hash_password(body.password))
    db.add(agent)
    return _save(db, agent)


@router.patch("/agents/{agent_id}", response_model=AgentOut)
def patch_agent(
    agent_id: int,
    body: AgentPatch,
    me: Agent = Depends(require_admin),
    db: Session = Depends(get_db),
):
    agent = _get(db, Agent, agent_id)
    changes = body.model_dump(exclude_unset=True)
    if agent.id == me.id and (
        changes.get("is_active") is False or changes.get("role", AgentRole.ADMIN) != AgentRole.ADMIN
    ):
        # Evita que el centro se quede sin administrador por un toque equivocado.
        raise HTTPException(status.HTTP_409_CONFLICT, "No puede quitarse sus propios permisos")
    if password := changes.pop("password", None):
        agent.password_hash = hash_password(password)
    for key, value in changes.items():
        setattr(agent, key, value)
    return _save(db, agent)


# --- Calendario hábil ------------------------------------------------------------------------


@router.get("/business-hours", response_model=ScheduleOut)
def get_schedule(area_id: int | None = None, db: Session = Depends(get_db)):
    """Horario de un área (o el por defecto si `area_id` se omite)."""
    rows = db.scalars(
        select(BusinessHours)
        .where(
            BusinessHours.area_id.is_(None) if area_id is None else BusinessHours.area_id == area_id
        )
        .order_by(BusinessHours.weekday, BusinessHours.opens_at)
    ).all()
    return ScheduleOut(
        area_id=area_id,
        inherits_default=area_id is not None and not rows,
        slots=[Slot(weekday=r.weekday, opens_at=r.opens_at, closes_at=r.closes_at) for r in rows],
    )


@router.put("/business-hours", response_model=ScheduleOut)
def put_schedule(body: ScheduleIn, area_id: int | None = None, db: Session = Depends(get_db)):
    """Reemplaza el horario completo. En un área, una lista vacía hereda el horario por defecto."""
    if area_id is not None:
        _get(db, Area, area_id)
    db.execute(
        delete(BusinessHours).where(
            BusinessHours.area_id.is_(None) if area_id is None else BusinessHours.area_id == area_id
        )
    )
    for slot in body.slots:
        db.add(BusinessHours(area_id=area_id, **slot.model_dump()))
    db.commit()
    return get_schedule(area_id, db)


@router.get("/holidays", response_model=list[HolidayOut])
def list_holidays(db: Session = Depends(get_db)):
    return db.scalars(select(Holiday).order_by(Holiday.day)).all()


@router.post("/holidays", response_model=HolidayOut, status_code=201)
def create_holiday(body: HolidayIn, db: Session = Depends(get_db)):
    holiday = Holiday(**body.model_dump())
    db.add(holiday)
    return _save(db, holiday)


@router.delete("/holidays/{holiday_id}", status_code=204)
def delete_holiday(holiday_id: int, db: Session = Depends(get_db)) -> None:
    db.delete(_get(db, Holiday, holiday_id))
    db.commit()
