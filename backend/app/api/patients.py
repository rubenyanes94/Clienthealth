from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_agent
from app.db.session import get_db
from app.models import Agent, Case, Patient
from app.schemas import CaseBrief
from app.schemas.cases import (
    PatientDetail,
    PatientIn,
    PatientOut,
    PatientPage,
    PatientPatch,
    PatientSearchIn,
)
from app.services import patients as svc

router = APIRouter(prefix="/patients", tags=["patients"])

PAGE_SIZE = 50


@router.post("/search", response_model=PatientPage)
def search(
    body: PatientSearchIn, _: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> PatientPage:
    offset = int(body.cursor) if body.cursor and body.cursor.isdigit() else 0
    query = select(Patient).order_by(Patient.last_name, Patient.first_name, Patient.id)
    if (match := svc.match_query(body.q)) is not None:
        query = query.where(match)
    rows = list(db.scalars(query.offset(offset).limit(PAGE_SIZE + 1)))
    return PatientPage(
        items=[PatientOut.model_validate(p) for p in rows[:PAGE_SIZE]],
        next_cursor=str(offset + PAGE_SIZE) if len(rows) > PAGE_SIZE else None,
    )


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create(
    body: PatientIn, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> Patient:
    return svc.create(db, agent, body.model_dump())


@router.get("/{patient_id}", response_model=PatientDetail)
def get_patient(
    patient_id: int, _: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> PatientDetail:
    out = PatientDetail.model_validate(svc.get(db, patient_id))
    rows = db.scalars(select(Case).where(Case.patient_id == patient_id).order_by(Case.id.desc()))
    out.cases = [CaseBrief.model_validate(c) for c in rows]
    return out


@router.patch("/{patient_id}", response_model=PatientOut)
def update(
    patient_id: int,
    body: PatientPatch,
    _: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> Patient:
    return svc.update(db, patient_id, body.model_dump(exclude_none=True))
