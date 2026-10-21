"""Indicadores calculados siempre desde `conversation_events` (ver docs/METRICAS.md).

El cálculo tiene dos pasos puros, sin base de datos:
1. `build_episodes`: recorre los eventos de una conversación y arma sus *episodios* de atención
   humana (desde que entra en cola hasta que se cierra).
2. `summarize` y compañía: agregan episodios, conversaciones y encuestas en KPIs.
`load_period` es la única parte que consulta la base.
"""

import math
import statistics
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Area, Conversation, ConversationEvent, Survey
from app.models.enums import EventType, SurveyKind, SurveyStatus
from app.services.business_time import Calendar, Interval, active_business_minutes, load_calendar

DEFAULT_SLA_MINUTES = 15


# --- Datos de entrada --------------------------------------------------------------------------


@dataclass(frozen=True)
class Ev:
    conversation_id: int
    type: EventType
    created_at: datetime
    agent_id: int | None = None
    area_id: int | None = None
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SurveyRow:
    kind: SurveyKind
    status: SurveyStatus
    score: int | None
    sent_at: datetime
    answered_at: datetime | None
    agent_id: int | None
    area_id: int | None


@dataclass
class Episode:
    """Un tramo de atención humana de una conversación."""

    conversation_id: int
    origin: str  # "queue" | "intervention" | "agent_reopen"
    start: datetime
    area_id: int | None
    accepted_at: datetime | None = None
    accepted_by: int | None = None
    first_response_at: datetime | None = None
    first_response_by: int | None = None
    pauses: list[Interval] = field(default_factory=list)
    pause_open: datetime | None = None
    transfers: int = 0
    abandoned_event: bool = False
    urgent: bool = False
    closed_at: datetime | None = None
    closed_by: str | None = None  # "agent" | "bot"
    closed_agent_id: int | None = None
    reason_id: int | None = None
    reopened_at: datetime | None = None


@dataclass
class ConversationFacts:
    conversation_id: int
    created_at: datetime | None = None
    bot_resolved: bool = False
    has_episode: bool = False

    @property
    def contained(self) -> bool:
        """Resuelta por el bot sin pasar nunca por un humano."""
        return self.bot_resolved and not self.has_episode


# --- 1. Episodios ------------------------------------------------------------------------------


def build_episodes(events: Iterable[Ev]) -> tuple[list[Episode], ConversationFacts | None]:
    """Eventos de UNA conversación, en orden cronológico."""
    episodes: list[Episode] = []
    facts: ConversationFacts | None = None
    current: Episode | None = None
    last_closed: Episode | None = None

    def start(origin: str, ev: Ev, area_id: int | None) -> Episode:
        episode = Episode(ev.conversation_id, origin, ev.created_at, area_id)
        episodes.append(episode)
        return episode

    for ev in events:
        if facts is None:
            facts = ConversationFacts(ev.conversation_id)
        match ev.type:
            case EventType.CREATED:
                facts.created_at = ev.created_at
            case EventType.BOT_RESOLVED:
                facts.bot_resolved = True
            case EventType.BOT_ESCALATED if current is None:
                current = start("queue", ev, ev.data.get("area_id", ev.area_id))
            case EventType.REOPENED:
                if last_closed is not None and last_closed.reopened_at is None:
                    last_closed.reopened_at = ev.created_at
                if current is None and ev.data.get("status") == "queued":
                    current = start("queue", ev, ev.area_id)
                elif current is None and ev.data.get("status") == "open":
                    current = start("agent_reopen", ev, ev.area_id)
                    current.accepted_at, current.accepted_by = ev.created_at, ev.agent_id
            case EventType.ACCEPTED:
                if current is None and ev.data.get("from_status") == "bot":
                    current = start("intervention", ev, ev.area_id)
                if current is not None and current.accepted_at is None:
                    current.accepted_at, current.accepted_by = ev.created_at, ev.agent_id

        if current is None:
            continue
        match ev.type:
            case EventType.AGENT_MESSAGE if ev.data.get("status") != "failed":
                if current.first_response_at is None:
                    current.first_response_at = ev.created_at
                    current.first_response_by = ev.agent_id
            case EventType.PENDING_STARTED:
                current.pause_open = ev.created_at
            case EventType.PENDING_RESUMED if current.pause_open is not None:
                current.pauses.append((current.pause_open, ev.created_at))
                current.pause_open = None
            case EventType.TRANSFERRED:
                current.transfers += 1
            case EventType.ABANDONED:
                current.abandoned_event = True
            case EventType.URGENCY_DETECTED:
                current.urgent = True
            case EventType.CLOSED:
                if current.pause_open is not None:
                    current.pauses.append((current.pause_open, ev.created_at))
                    current.pause_open = None
                current.closed_at = ev.created_at
                current.closed_by = ev.data.get("by", "agent")
                current.closed_agent_id = ev.agent_id
                current.reason_id = ev.data.get("reason_id")
                last_closed, current = current, None

    if facts is not None:
        facts.has_episode = bool(episodes)
    return episodes, facts


# --- 2. Medidas por episodio -------------------------------------------------------------------


@dataclass(frozen=True)
class Rules:
    calendar: Calendar
    now: datetime
    sla_by_area: dict[int, int]
    reopen_window: timedelta
    abandon_after: timedelta


def _pauses_until(episode: Episode, now: datetime) -> list[Interval]:
    pauses = list(episode.pauses)
    if episode.pause_open is not None:
        pauses.append((episode.pause_open, now))
    return pauses


def first_response_minutes(episode: Episode, rules: Rules) -> float | None:
    if episode.origin == "agent_reopen" or episode.first_response_at is None:
        return None
    return active_business_minutes(
        episode.start, episode.first_response_at, episode.pauses, rules.calendar, episode.area_id
    )


def resolution_minutes(episode: Episode, rules: Rules) -> float | None:
    if episode.closed_by != "agent" or episode.closed_at is None:
        return None
    return active_business_minutes(
        episode.start, episode.closed_at, episode.pauses, rules.calendar, episode.area_id
    )


def sla_status(episode: Episode, rules: Rules) -> str | None:
    """ "met", "breached" o None (no aplica / aún dentro de plazo)."""
    if episode.origin == "agent_reopen":
        return None
    goal = rules.sla_by_area.get(episode.area_id or 0, DEFAULT_SLA_MINUTES)
    frt = first_response_minutes(episode, rules)
    if frt is not None:
        return "met" if frt <= goal else "breached"
    if episode.closed_at is not None:
        return None  # cerrado sin respuesta humana: se excluye
    waited = active_business_minutes(
        episode.start, rules.now, _pauses_until(episode, rules.now), rules.calendar, episode.area_id
    )
    return "breached" if waited > goal else None


def is_abandoned(episode: Episode, rules: Rules) -> bool:
    if episode.origin == "agent_reopen" or episode.first_response_at is not None:
        return False
    if episode.abandoned_event:
        return True
    return episode.closed_at is None and rules.now - episode.start >= rules.abandon_after


def fcr(episode: Episode, rules: Rules) -> bool | None:
    """Resuelto al primer contacto: cerrado por agente, sin transferencias y sin reapertura
    dentro de la ventana. None mientras la ventana no haya pasado."""
    if episode.closed_by != "agent" or episode.closed_at is None:
        return None
    if episode.reopened_at is not None and (
        episode.reopened_at - episode.closed_at < rules.reopen_window
    ):
        return False
    if episode.transfers > 0:
        return False
    if rules.now - episode.closed_at >= rules.reopen_window:
        return True
    return None


def was_reopened(episode: Episode, rules: Rules) -> bool:
    return (
        episode.closed_at is not None
        and episode.reopened_at is not None
        and episode.reopened_at - episode.closed_at < rules.reopen_window
    )


# --- 3. Agregados ------------------------------------------------------------------------------


def ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "value": round(numerator / denominator, 4) if denominator else None,
        "numerator": numerator,
        "denominator": denominator,
    }


def durations(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "avg": None, "median": None, "p90": None}
    ordered = sorted(values)
    p90 = ordered[max(0, math.ceil(0.9 * len(ordered)) - 1)]
    return {
        "count": len(values),
        "avg": round(statistics.fmean(values), 1),
        "median": round(statistics.median(values), 1),
        "p90": round(p90, 1),
    }


def csat_summary(surveys: list[SurveyRow]) -> dict[str, Any]:
    csat = [s for s in surveys if s.kind == SurveyKind.CSAT]
    answered = [s.score for s in csat if s.status == SurveyStatus.ANSWERED and s.score is not None]
    sent = [s for s in csat if s.status != SurveyStatus.FAILED]
    return {
        "responses": len(answered),
        "sent": len(sent),
        "response_rate": ratio(len(answered), len(sent)),
        "avg": round(statistics.fmean(answered), 2) if answered else None,
        "satisfied": ratio(sum(1 for s in answered if s >= 4), len(answered)),
    }


def nps_summary(surveys: list[SurveyRow]) -> dict[str, Any]:
    scores = [
        s.score
        for s in surveys
        if s.kind == SurveyKind.NPS and s.status == SurveyStatus.ANSWERED and s.score is not None
    ]
    promoters = sum(1 for s in scores if s >= 9)
    detractors = sum(1 for s in scores if s <= 6)
    return {
        "responses": len(scores),
        "promoters": promoters,
        "passives": len(scores) - promoters - detractors,
        "detractors": detractors,
        "score": round(100 * (promoters - detractors) / len(scores), 1) if scores else None,
    }


def summarize(
    episodes: list[Episode],
    conversations: list[ConversationFacts],
    surveys: list[SurveyRow],
    urgent: int,
    rules: Rules,
) -> dict[str, Any]:
    frts = [m for e in episodes if (m := first_response_minutes(e, rules)) is not None]
    resolutions = [m for e in episodes if (m := resolution_minutes(e, rules)) is not None]
    sla = [s for e in episodes if (s := sla_status(e, rules)) is not None]
    fcrs = [f for e in episodes if (f := fcr(e, rules)) is not None]
    closed_by_agent = [e for e in episodes if e.closed_by == "agent"]
    human = [e for e in episodes if e.origin != "agent_reopen"]
    return {
        "conversations": len(conversations),
        "episodes": len(episodes),
        "urgent": urgent,
        "first_response": durations(frts),
        "sla": ratio(sla.count("met"), len(sla)),
        "resolution_time": durations(resolutions),
        "resolution_rate": ratio(sum(1 for e in episodes if e.closed_at), len(episodes)),
        "fcr": ratio(sum(fcrs), len(fcrs)),
        "reopen_rate": ratio(
            sum(1 for e in closed_by_agent if was_reopened(e, rules)), len(closed_by_agent)
        ),
        "transfer_rate": ratio(sum(1 for e in episodes if e.transfers > 0), len(episodes)),
        "abandon_rate": ratio(sum(1 for e in human if is_abandoned(e, rules)), len(human)),
        "bot_containment": ratio(sum(1 for c in conversations if c.contained), len(conversations)),
        "csat": csat_summary(surveys),
        "nps": nps_summary(surveys),
    }


# --- Carga desde la base -----------------------------------------------------------------------


@dataclass
class Period:
    date_from: date
    date_to: date  # inclusive
    tz: ZoneInfo
    start: datetime
    end: datetime

    def contains(self, moment: datetime | None) -> bool:
        return moment is not None and self.start <= moment < self.end

    def local_day(self, moment: datetime) -> date:
        return moment.astimezone(self.tz).date()

    def local_hour(self, moment: datetime) -> int:
        return moment.astimezone(self.tz).hour


def make_period(date_from: date, date_to: date) -> Period:
    tz = ZoneInfo(get_settings().timezone)
    start = datetime.combine(date_from, datetime.min.time(), tzinfo=tz)
    end = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=tz)
    return Period(date_from, date_to, tz, start, end)


@dataclass
class PeriodData:
    period: Period
    rules: Rules
    episodes: list[Episode]  # con inicio dentro del período
    conversations: list[ConversationFacts]  # creadas dentro del período
    surveys: list[SurveyRow]  # respondidas (o enviadas, si no hay respuesta) en el período
    events: list[Ev]  # todos los eventos de las conversaciones cargadas
    area_filter: int | None


def load_period(
    db: Session, date_from: date, date_to: date, area_id: int | None, now: datetime
) -> PeriodData:
    settings = get_settings()
    period = make_period(date_from, date_to)
    rules = Rules(
        calendar=load_calendar(db),
        now=now,
        sla_by_area={a.id: a.sla_first_response_minutes for a in db.scalars(select(Area))},
        reopen_window=timedelta(hours=settings.reopen_window_hours),
        abandon_after=timedelta(hours=settings.abandon_after_hours),
    )

    touched = (
        select(ConversationEvent.conversation_id)
        .where(
            ConversationEvent.created_at >= period.start,
            ConversationEvent.created_at < period.end,
        )
        .distinct()
    )
    rows = db.scalars(
        select(ConversationEvent)
        .where(ConversationEvent.conversation_id.in_(touched))
        .order_by(
            ConversationEvent.conversation_id, ConversationEvent.created_at, ConversationEvent.id
        )
    )
    by_conversation: dict[int, list[Ev]] = defaultdict(list)
    for row in rows:
        by_conversation[row.conversation_id].append(
            Ev(row.conversation_id, row.type, row.created_at, row.agent_id, row.area_id, row.data)
        )

    episodes: list[Episode] = []
    conversations: list[ConversationFacts] = []
    all_events: list[Ev] = []
    for evs in by_conversation.values():
        all_events.extend(evs)
        conv_episodes, facts = build_episodes(evs)
        episodes.extend(
            e
            for e in conv_episodes
            if period.contains(e.start) and (area_id is None or e.area_id == area_id)
        )
        if facts and period.contains(facts.created_at) and area_id is None:
            conversations.append(facts)

    survey_query = (
        select(Survey, Conversation.area_id)
        .join(Conversation, Conversation.id == Survey.conversation_id)
        .where(Survey.sent_at < period.end)
        .where(
            (Survey.answered_at >= period.start)
            | ((Survey.answered_at.is_(None)) & (Survey.sent_at >= period.start))
        )
    )
    if area_id is not None:
        survey_query = survey_query.where(Conversation.area_id == area_id)
    surveys = [
        SurveyRow(s.kind, s.status, s.score, s.sent_at, s.answered_at, s.agent_id, area)
        for s, area in db.execute(survey_query)
        if s.answered_at is None or period.contains(s.answered_at)
    ]
    return PeriodData(period, rules, episodes, conversations, surveys, all_events, area_id)


def count_urgent(data: PeriodData, keep: Callable[[Ev], bool] = lambda _: True) -> int:
    return sum(
        1
        for ev in data.events
        if ev.type == EventType.URGENCY_DETECTED
        and data.period.contains(ev.created_at)
        and (data.area_filter is None or ev.area_id == data.area_filter)
        and keep(ev)
    )


# --- Vistas para los paneles -------------------------------------------------------------------


def overview(data: PeriodData) -> dict[str, Any]:
    return summarize(
        data.episodes, data.conversations, data.surveys, count_urgent(data), data.rules
    )


def by_hour(data: PeriodData) -> list[dict[str, Any]]:
    inbound: dict[int, int] = defaultdict(int)
    for ev in data.events:
        if ev.type == EventType.INBOUND_MESSAGE and data.period.contains(ev.created_at):
            if data.area_filter is None or ev.area_id == data.area_filter:
                inbound[data.period.local_hour(ev.created_at)] += 1
    grouped: dict[int, list[Episode]] = defaultdict(list)
    for episode in data.episodes:
        grouped[data.period.local_hour(episode.start)].append(episode)
    rows = []
    for hour in range(24):
        episodes = grouped.get(hour, [])
        frts = [m for e in episodes if (m := first_response_minutes(e, data.rules)) is not None]
        sla = [s for e in episodes if (s := sla_status(e, data.rules)) is not None]
        rows.append(
            {
                "hour": hour,
                "inbound_messages": inbound.get(hour, 0),
                "episodes": len(episodes),
                "first_response_median": durations(frts)["median"],
                "sla": ratio(sla.count("met"), len(sla)),
            }
        )
    return rows


def by_area(data: PeriodData, areas: dict[int, str]) -> list[dict[str, Any]]:
    grouped: dict[int | None, list[Episode]] = defaultdict(list)
    for episode in data.episodes:
        grouped[episode.area_id].append(episode)
    surveys: dict[int | None, list[SurveyRow]] = defaultdict(list)
    for survey in data.surveys:
        surveys[survey.area_id].append(survey)
    rows = []
    for area_id in sorted(set(grouped) | set(surveys), key=lambda a: (a is None, a or 0)):
        summary = summarize(
            grouped.get(area_id, []),
            [],
            surveys.get(area_id, []),
            count_urgent(data, lambda ev, a=area_id: ev.area_id == a),
            data.rules,
        )
        rows.append({"area_id": area_id, "name": areas.get(area_id or 0, "Sin área"), **summary})
    return rows


def by_agent(data: PeriodData, agents: dict[int, str]) -> list[dict[str, Any]]:
    stats: dict[int, dict[str, Any]] = defaultdict(
        lambda: {"accepted": 0, "frts": [], "closed": 0, "resolutions": [], "fcr": [], "csat": []}
    )
    for e in data.episodes:
        if e.accepted_by is not None and e.origin != "agent_reopen":
            stats[e.accepted_by]["accepted"] += 1
        if e.first_response_by is not None:
            if (m := first_response_minutes(e, data.rules)) is not None:
                stats[e.first_response_by]["frts"].append(m)
        if e.closed_by == "agent" and e.closed_agent_id is not None:
            row = stats[e.closed_agent_id]
            row["closed"] += 1
            if (m := resolution_minutes(e, data.rules)) is not None:
                row["resolutions"].append(m)
            if (f := fcr(e, data.rules)) is not None:
                row["fcr"].append(f)
    for s in data.surveys:
        if s.kind == SurveyKind.CSAT and s.agent_id is not None:
            stats[s.agent_id]["csat"].append(s)
    rows = []
    for agent_id, row in stats.items():
        rows.append(
            {
                "agent_id": agent_id,
                "name": agents.get(agent_id, f"Agente {agent_id}"),
                "accepted": row["accepted"],
                "first_response": durations(row["frts"]),
                "closed": row["closed"],
                "resolution_time": durations(row["resolutions"]),
                "fcr": ratio(sum(row["fcr"]), len(row["fcr"])),
                "csat": csat_summary(row["csat"]),
            }
        )
    return sorted(rows, key=lambda r: (-r["closed"], r["name"]))


def reasons(data: PeriodData, names: dict[int, str]) -> list[dict[str, Any]]:
    """Motivos de los casos cerrados por agentes dentro del período (por fecha de cierre)."""
    counts: dict[int | None, int] = defaultdict(int)
    for ev in data.events:
        if (
            ev.type == EventType.CLOSED
            and ev.data.get("by", "agent") == "agent"
            and data.period.contains(ev.created_at)
            and (data.area_filter is None or ev.area_id == data.area_filter)
        ):
            counts[ev.data.get("reason_id")] += 1
    total = sum(counts.values())
    rows = [
        {
            "reason_id": reason_id,
            "name": names.get(reason_id or 0, "Sin motivo"),
            "count": count,
            "share": ratio(count, total)["value"],
        }
        for reason_id, count in counts.items()
    ]
    return sorted(rows, key=lambda r: -r["count"])


def csat_daily(data: PeriodData) -> list[dict[str, Any]]:
    by_day: dict[date, list[SurveyRow]] = defaultdict(list)
    for s in data.surveys:
        if s.kind == SurveyKind.CSAT and s.answered_at is not None:
            by_day[data.period.local_day(s.answered_at)].append(s)
    rows = []
    day = data.period.date_from
    while day <= data.period.date_to:
        summary = csat_summary(by_day.get(day, []))
        rows.append(
            {
                "day": day,
                "responses": summary["responses"],
                "avg": summary["avg"],
                "satisfied": summary["satisfied"]["value"],
            }
        )
        day += timedelta(days=1)
    return rows
