"""Minutos hábiles entre dos instantes, según el horario y los feriados de cada área.

Funciones puras sobre un `Calendar` ya cargado: no consultan la base en cada cálculo.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import BusinessHours, Holiday

Interval = tuple[datetime, datetime]
Slots = dict[int, list[tuple[time, time]]]  # weekday -> franjas


@dataclass
class Calendar:
    tz: ZoneInfo
    default: Slots = field(default_factory=dict)
    by_area: dict[int, Slots] = field(default_factory=dict)
    holidays_all: set[date] = field(default_factory=set)
    holidays_by_area: dict[int, set[date]] = field(default_factory=dict)

    def slots_for(self, area_id: int | None) -> Slots:
        if area_id is not None and area_id in self.by_area:
            return self.by_area[area_id]
        return self.default

    def is_holiday(self, day: date, area_id: int | None) -> bool:
        return day in self.holidays_all or (
            area_id is not None and day in self.holidays_by_area.get(area_id, set())
        )


def load_calendar(db: Session) -> Calendar:
    calendar = Calendar(tz=ZoneInfo(get_settings().timezone))
    for row in db.scalars(select(BusinessHours)):
        target: Slots
        if row.area_id is None:
            target = calendar.default
        else:
            target = calendar.by_area.setdefault(row.area_id, {})
        target.setdefault(row.weekday, []).append((row.opens_at, row.closes_at))
    by_area: dict[int, set[date]] = defaultdict(set)
    for holiday in db.scalars(select(Holiday)):
        if holiday.area_id is None:
            calendar.holidays_all.add(holiday.day)
        else:
            by_area[holiday.area_id].add(holiday.day)
    calendar.holidays_by_area = dict(by_area)
    return calendar


def business_minutes(
    start: datetime, end: datetime, calendar: Calendar, area_id: int | None
) -> float:
    """Minutos de [start, end) que caen en horario hábil del área."""
    if end <= start:
        return 0.0
    slots = calendar.slots_for(area_id)
    if not slots:  # sin horario configurado: minutos de reloj
        return (end - start).total_seconds() / 60

    tz = calendar.tz
    local_start, local_end = start.astimezone(tz), end.astimezone(tz)
    total = 0.0
    day = local_start.date()
    while day <= local_end.date():
        if not calendar.is_holiday(day, area_id):
            for opens, closes in slots.get(day.weekday(), []):
                window_start = datetime.combine(day, opens, tzinfo=tz)
                window_end = datetime.combine(day, closes, tzinfo=tz)
                overlap_start = max(window_start, local_start)
                overlap_end = min(window_end, local_end)
                if overlap_end > overlap_start:
                    total += (overlap_end - overlap_start).total_seconds() / 60
        day += timedelta(days=1)
    return total


def active_business_minutes(
    start: datetime,
    end: datetime,
    pauses: Iterable[Interval],
    calendar: Calendar,
    area_id: int | None,
) -> float:
    """Minutos hábiles de [start, end) descontando las pausas (caso en espera del paciente)."""
    total = business_minutes(start, end, calendar, area_id)
    for pause_start, pause_end in pauses:
        clipped_start, clipped_end = max(pause_start, start), min(pause_end, end)
        total -= business_minutes(clipped_start, clipped_end, calendar, area_id)
    return max(total, 0.0)
