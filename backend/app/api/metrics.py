from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_supervisor
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Agent, Area, ContactReason
from app.schemas.metrics import AgentRow, AreaRow, CsatDay, HourRow, OverviewOut, ReasonRow
from app.services import metrics

router = APIRouter(prefix="/metrics", tags=["metrics"], dependencies=[Depends(require_supervisor)])

MAX_DAYS = 366


def period_data(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    area_id: int | None = None,
    db: Session = Depends(get_db),
) -> metrics.PeriodData:
    if date_to < date_from:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "«to» es anterior a «from»")
    if date_to - date_from > timedelta(days=MAX_DAYS):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El período máximo es un año")
    return metrics.load_period(db, date_from, date_to, area_id, utcnow())


@router.get("/overview", response_model=OverviewOut)
def overview(data: metrics.PeriodData = Depends(period_data)):
    return {
        **metrics.overview(data),
        "date_from": data.period.date_from,
        "date_to": data.period.date_to,
    }


@router.get("/by-hour", response_model=list[HourRow])
def by_hour(data: metrics.PeriodData = Depends(period_data)):
    return metrics.by_hour(data)


@router.get("/by-area", response_model=list[AreaRow])
def by_area(data: metrics.PeriodData = Depends(period_data), db: Session = Depends(get_db)):
    return metrics.by_area(data, {a.id: a.name for a in db.scalars(select(Area))})


@router.get("/by-agent", response_model=list[AgentRow])
def by_agent(data: metrics.PeriodData = Depends(period_data), db: Session = Depends(get_db)):
    return metrics.by_agent(data, {a.id: a.name for a in db.scalars(select(Agent))})


@router.get("/reasons", response_model=list[ReasonRow])
def reasons(data: metrics.PeriodData = Depends(period_data), db: Session = Depends(get_db)):
    return metrics.reasons(data, {r.id: r.name for r in db.scalars(select(ContactReason))})


@router.get("/csat-daily", response_model=list[CsatDay])
def csat_daily(data: metrics.PeriodData = Depends(period_data)):
    return metrics.csat_daily(data)
