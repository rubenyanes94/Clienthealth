from fastapi import APIRouter, Depends, status
from sqlalchemy import case as sql_case
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_agent
from app.core.config import get_settings
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Agent, Case, CaseNote, Patient
from app.models.enums import CaseStage, Priority
from app.schemas.cases import (
    CaseDetail,
    CaseIn,
    CaseNoteIn,
    CaseNoteOut,
    CasePage,
    CasePatch,
    CaseSearchIn,
    CasesLive,
    CaseStageIn,
    CaseSummary,
    CaseTransferIn,
)
from app.services import cases as svc
from app.services import conversations

router = APIRouter(prefix="/cases", tags=["cases"])

PAGE_SIZE = 50


def to_detail(db: Session, agent: Agent, case: Case) -> CaseDetail:
    db.refresh(case)
    out = CaseDetail.model_validate({**_attrs(case), "next_stages": svc.NEXT_STAGES[case.stage]})
    out.can_view_conversation = bool(
        case.conversation and conversations.can_view(agent, case.conversation)
    )
    return out


def _attrs(case: Case) -> dict:
    return {name: getattr(case, name) for name in CaseDetail.model_fields if hasattr(case, name)}


@router.post("/search", response_model=CasePage)
def search(
    body: CaseSearchIn, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> CasePage:
    offset = int(body.cursor) if body.cursor and body.cursor.isdigit() else 0
    filters = svc.search_filters(
        agent, stage=body.stage, area_id=body.area_id, mine=body.mine, q=body.q
    )
    query = (
        select(Case)
        .join(Patient, Case.patient_id == Patient.id)
        .where(*filters)
        .options(
            selectinload(Case.patient),
            selectinload(Case.area),
            selectinload(Case.assigned_agent),
        )
    )
    if body.stage == "closed":
        query = query.order_by(Case.closed_at.desc(), Case.id.desc())
    else:
        # Urgentes primero; después, lo que lleva más tiempo sin moverse.
        urgent_first = sql_case((Case.priority == Priority.HIGH, 0), else_=1)
        closed_last = sql_case((Case.stage == CaseStage.CLOSED, 1), else_=0)
        query = query.order_by(closed_last, urgent_first, Case.stage_changed_at, Case.id)
    rows = list(db.scalars(query.offset(offset).limit(PAGE_SIZE + 1)))
    return CasePage(
        items=[CaseSummary.model_validate(c) for c in rows[:PAGE_SIZE]],
        next_cursor=str(offset + PAGE_SIZE) if len(rows) > PAGE_SIZE else None,
        goal_minutes=get_settings().case_goal_minutes,
    )


@router.get("/live", response_model=CasesLive)
def live(_: Agent = Depends(current_agent), db: Session = Depends(get_db)):
    return svc.live(db, utcnow())


@router.post("", response_model=CaseDetail, status_code=status.HTTP_201_CREATED)
def create(
    body: CaseIn, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> CaseDetail:
    return to_detail(db, agent, svc.create(db, agent, **body.model_dump()))


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> CaseDetail:
    return to_detail(db, agent, svc.get(db, case_id))


@router.patch("/{case_id}", response_model=CaseDetail)
def update(
    case_id: int,
    body: CasePatch,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> CaseDetail:
    fields = body.model_dump(exclude_none=True)
    return to_detail(db, agent, svc.update(db, agent, case_id, fields))


@router.post("/{case_id}/stage", response_model=CaseDetail)
def change_stage(
    case_id: int,
    body: CaseStageIn,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> CaseDetail:
    case = svc.change_stage(db, agent, case_id, body.stage, body.contact_reason_id)
    return to_detail(db, agent, case)


@router.post("/{case_id}/transfer", response_model=CaseDetail)
def transfer(
    case_id: int,
    body: CaseTransferIn,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> CaseDetail:
    return to_detail(db, agent, svc.transfer(db, agent, case_id, body.area_id))


@router.post("/{case_id}/take", response_model=CaseDetail)
def take(
    case_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> CaseDetail:
    return to_detail(db, agent, svc.take(db, agent, case_id))


@router.post("/{case_id}/notes", response_model=CaseNoteOut, status_code=status.HTTP_201_CREATED)
def add_note(
    case_id: int,
    body: CaseNoteIn,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> CaseNote:
    return svc.add_note(db, agent, case_id, body.body)
