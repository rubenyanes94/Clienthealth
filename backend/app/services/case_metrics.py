"""Indicadores del módulo de Casos para Paneles e Informes. Definiciones en docs/METRICAS.md.

Un caso que pasa por varias áreas tiene un *tramo* en cada una: así cada área responde por su
propio tiempo. Funciones puras sobre los eventos; solo `load_period` consulta la base.
"""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Case, CaseEvent
from app.models.enums import CaseEventType, Priority
from app.services.business_time import Calendar, business_minutes, load_calendar
from app.services.metrics import Period, durations, make_period, ratio


@dataclass
class Ev:
    type: CaseEventType
    created_at: datetime
    agent_id: int | None
    area_id: int | None
    data: dict[str, Any]


@dataclass
class Span:
    start: datetime
    end: datetime
    agent_id: int | None  # quien lo puso en esta etapa


@dataclass
class Stay:
    """Paso de un caso por un área: desde que entra hasta que se resuelve o se transfiere."""

    area_id: int
    start: datetime
    first_attention_at: datetime | None = None
    attended_by: int | None = None
    end: datetime | None = None
    transferred: bool = False
    attention: list[Span] = field(default_factory=list)
    waiting: list[Span] = field(default_factory=list)


@dataclass
class CaseFacts:
    case_id: int
    created_at: datetime
    stays: list[Stay]
    events: list[Ev]
    was_closed: bool = False
    was_reopened: bool = False
    priority: Priority = Priority.NORMAL
    reason_id: int | None = None

    @property
    def transferred(self) -> bool:
        return len(self.stays) > 1

    @property
    def resolved(self) -> bool:
        return (
            bool(self.stays) and self.stays[-1].end is not None and not self.stays[-1].transferred
        )


def build_facts(case_id: int, events: Iterable[Ev]) -> CaseFacts | None:
    stays: list[Stay] = []
    evs = list(events)
    stage, since, by = "registered", None, None
    facts: CaseFacts | None = None

    def close_span(until: datetime) -> None:
        if since is None:
            return
        if stage == "in_progress":
            stays[-1].attention.append(Span(since, until, by))
        elif stage == "waiting":
            stays[-1].waiting.append(Span(since, until, by))

    for ev in evs:
        if ev.type == CaseEventType.CREATED:
            stays.append(Stay(area_id=ev.data["area_id"], start=ev.created_at))
            facts = CaseFacts(case_id, ev.created_at, stays, evs)
            stage, since, by = "registered", ev.created_at, ev.agent_id
        elif facts is None:
            continue
        elif ev.type == CaseEventType.STAGE_CHANGED:
            close_span(ev.created_at)
            to = ev.data["to"]
            stay = stays[-1]
            if to == "in_progress":
                if stay.first_attention_at is None:
                    stay.first_attention_at = ev.created_at
                    stay.attended_by = ev.agent_id
                if ev.data["from"] == "closed":
                    facts.was_reopened = True
                stay.end = None
            elif to == "resolved":
                stay.end = ev.created_at
            elif to == "closed":
                facts.was_closed = True
            stage, since, by = to, ev.created_at, ev.agent_id
        elif ev.type == CaseEventType.TRANSFERRED:
            close_span(ev.created_at)
            stays[-1].end = ev.created_at
            stays[-1].transferred = True
            stays.append(Stay(area_id=ev.data["to_area_id"], start=ev.created_at))
            stage, since, by = "registered", ev.created_at, ev.agent_id
    return facts


# --- Cálculo por tramo -------------------------------------------------------------------------


def time_to_attention(stay: Stay, calendar: Calendar) -> float | None:
    if stay.first_attention_at is None:
        return None
    return business_minutes(stay.start, stay.first_attention_at, calendar, stay.area_id)


def goal_status(stay: Stay, calendar: Calendar, goal: int, now: datetime) -> str | None:
    """ "met", "missed" o None si aún no se puede juzgar (sin atender y dentro de la meta)."""
    minutes = time_to_attention(stay, calendar)
    if minutes is not None:
        return "met" if minutes <= goal else "missed"
    waited = business_minutes(stay.start, stay.end or now, calendar, stay.area_id)
    return "missed" if waited > goal else None


def _spans_minutes(spans: list[Span], calendar: Calendar, area_id: int) -> float:
    return sum(business_minutes(s.start, s.end, calendar, area_id) for s in spans)


def attention_minutes(stay: Stay, calendar: Calendar) -> float | None:
    """Tiempo en «En atención». Solo tramos terminados: uno en curso aún no tiene valor final."""
    if stay.end is None or stay.first_attention_at is None:
        return None
    return _spans_minutes(stay.attention, calendar, stay.area_id)


def waiting_minutes(stay: Stay, calendar: Calendar) -> float | None:
    """Solo tramos que estuvieron en espera: los demás no deben arrastrar la mediana a cero."""
    if stay.end is None or not stay.waiting:
        return None
    return _spans_minutes(stay.waiting, calendar, stay.area_id)


def resolution_minutes(facts: CaseFacts, calendar: Calendar) -> float | None:
    """Tiempo por atender más tiempo en atención, en todas las áreas. Sin esperas ni reaperturas."""
    if not facts.resolved:
        return None
    total = 0.0
    for stay in facts.stays:
        until = stay.first_attention_at or stay.end
        total += business_minutes(stay.start, until, calendar, stay.area_id)
        total += _spans_minutes(stay.attention, calendar, stay.area_id)
    return total


# --- Período -----------------------------------------------------------------------------------


@dataclass
class CasePeriod:
    period: Period
    calendar: Calendar
    goal: int
    now: datetime
    area_filter: int | None
    facts: list[CaseFacts]

    def stays(self) -> list[Stay]:
        return [
            stay
            for f in self.facts
            for stay in f.stays
            if self.period.contains(stay.start)
            and (self.area_filter is None or stay.area_id == self.area_filter)
        ]

    def cohort(self) -> list[CaseFacts]:
        """Casos creados en el período. Con filtro: los que han pasado por el área."""
        return [
            f
            for f in self.facts
            if self.period.contains(f.created_at)
            and (self.area_filter is None or any(s.area_id == self.area_filter for s in f.stays))
        ]

    def closures(self) -> list[tuple[CaseFacts, Ev]]:
        return [
            (f, ev)
            for f in self.facts
            for ev in f.events
            if ev.type == CaseEventType.STAGE_CHANGED
            and ev.data["to"] == "closed"
            and self.period.contains(ev.created_at)
            and (self.area_filter is None or ev.area_id == self.area_filter)
        ]


def load_period(
    db: Session, date_from: date, date_to: date, area_id: int | None, now: datetime
) -> CasePeriod:
    period = make_period(date_from, date_to)
    touched = (
        select(CaseEvent.case_id)
        .where(CaseEvent.created_at >= period.start, CaseEvent.created_at < period.end)
        .distinct()
    )
    by_case: dict[int, list[Ev]] = defaultdict(list)
    rows = db.scalars(
        select(CaseEvent).where(CaseEvent.case_id.in_(touched)).order_by(CaseEvent.id)
    )
    for row in rows:
        by_case[row.case_id].append(
            Ev(row.type, row.created_at, row.agent_id, row.area_id, row.data)
        )
    cases = {c.id: c for c in db.scalars(select(Case).where(Case.id.in_(by_case)))}

    facts = []
    for case_id, events in by_case.items():
        built = build_facts(case_id, events)
        if built is not None:
            built.priority = cases[case_id].priority
            built.reason_id = cases[case_id].contact_reason_id
            facts.append(built)
    return CasePeriod(
        period, load_calendar(db), get_settings().case_goal_minutes, now, area_id, facts
    )


def _present(values: Iterable[float | None]) -> list[float]:
    return [v for v in values if v is not None]


def _stay_summary(stays: list[Stay], closed: int, data: CasePeriod) -> dict[str, Any]:
    statuses = [goal_status(s, data.calendar, data.goal, data.now) for s in stays]
    met, missed = statuses.count("met"), statuses.count("missed")
    return {
        "received": len(stays),
        "closed": closed,
        "time_to_attention": durations(
            _present(time_to_attention(s, data.calendar) for s in stays)
        ),
        "goal": ratio(met, met + missed),
        "attention_time": durations(_present(attention_minutes(s, data.calendar) for s in stays)),
        "waiting_time": durations(_present(waiting_minutes(s, data.calendar) for s in stays)),
    }


def overview(data: CasePeriod) -> dict[str, Any]:
    cohort = data.cohort()
    resolution = _present(resolution_minutes(f, data.calendar) for f in cohort)
    closed_once = [f for f in cohort if f.was_closed]
    return {
        **_stay_summary(data.stays(), len(data.closures()), data),
        "date_from": data.period.date_from,
        "date_to": data.period.date_to,
        "goal_minutes": data.goal,
        "created": len(cohort),
        "urgent": sum(f.priority == Priority.HIGH for f in cohort),
        "resolution_time": durations(resolution),
        "resolution_rate": ratio(sum(f.resolved for f in cohort), len(cohort)),
        "transfer_rate": ratio(sum(f.transferred for f in cohort), len(cohort)),
        "reopen_rate": ratio(sum(f.was_reopened for f in closed_once), len(closed_once)),
    }


def by_area(data: CasePeriod, areas: dict[int, str]) -> list[dict[str, Any]]:
    stays: dict[int, list[Stay]] = defaultdict(list)
    for stay in data.stays():
        stays[stay.area_id].append(stay)
    closed: dict[int, int] = defaultdict(int)
    for _, ev in data.closures():
        if ev.area_id is not None:
            closed[ev.area_id] += 1
    rows = [
        {
            "area_id": area_id,
            "name": areas.get(area_id, f"Área {area_id}"),
            **_stay_summary(stays[area_id], closed[area_id], data),
        }
        for area_id in stays.keys() | closed.keys()
    ]
    return sorted(rows, key=lambda r: (-r["received"], r["name"]))


def by_agent(data: CasePeriod, agents: dict[int, str]) -> list[dict[str, Any]]:
    """Por la persona que hizo cada cosa, según el evento que registró con su cuenta."""
    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    minutes: dict[int, list[float]] = defaultdict(list)
    for f in data.facts:
        for ev in f.events:
            if (
                ev.agent_id is None
                or not data.period.contains(ev.created_at)
                or (data.area_filter is not None and ev.area_id != data.area_filter)
            ):
                continue
            if ev.type == CaseEventType.TRANSFERRED:
                counts[ev.agent_id]["transferred"] += 1
            elif ev.type == CaseEventType.STAGE_CHANGED and ev.data["to"] in ("resolved", "closed"):
                counts[ev.agent_id][ev.data["to"]] += 1
        for stay in f.stays:
            if data.area_filter is not None and stay.area_id != data.area_filter:
                continue
            if stay.attended_by is not None and data.period.contains(stay.first_attention_at):
                counts[stay.attended_by]["attended"] += 1
            per_agent: dict[int, float] = defaultdict(float)
            for span in stay.attention:
                if span.agent_id is not None and data.period.contains(span.start):
                    per_agent[span.agent_id] += business_minutes(
                        span.start, span.end, data.calendar, stay.area_id
                    )
            for agent_id, total in per_agent.items():
                minutes[agent_id].append(total)
    rows = [
        {
            "agent_id": agent_id,
            "name": agents.get(agent_id, f"Agente {agent_id}"),
            "attended": counts[agent_id]["attended"],
            "resolved": counts[agent_id]["resolved"],
            "closed": counts[agent_id]["closed"],
            "transferred": counts[agent_id]["transferred"],
            "attention_time": durations(minutes[agent_id]),
        }
        for agent_id in counts.keys() | minutes.keys()
    ]
    return sorted(rows, key=lambda r: (-r["attended"], r["name"]))


def reasons(data: CasePeriod, names: dict[int, str]) -> list[dict[str, Any]]:
    counts: dict[int | None, int] = defaultdict(int)
    for f, _ in data.closures():
        counts[f.reason_id] += 1
    total = sum(counts.values())
    rows = [
        {
            "reason_id": reason_id,
            "name": names.get(reason_id, "Sin motivo") if reason_id is not None else "Sin motivo",
            "count": count,
            "share": count / total if total else None,
        }
        for reason_id, count in counts.items()
    ]
    return sorted(rows, key=lambda r: (-r["count"], r["name"]))
