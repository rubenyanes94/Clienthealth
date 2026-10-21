"""Escenarios de eventos fijos con el valor esperado de cada KPI (criterio de la fase 3)."""

from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.models.enums import EventType as T
from app.models.enums import SurveyKind, SurveyStatus
from app.services.business_time import Calendar
from app.services.metrics import (
    Ev,
    Rules,
    SurveyRow,
    build_episodes,
    by_agent,
    csat_summary,
    nps_summary,
    summarize,
)

CCS = ZoneInfo("America/Caracas")
AREA_1, AREA_2 = 1, 2


def at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=CCS)


def rules(now: datetime) -> Rules:
    week = {d: [(time(7), time(19))] for d in range(5)}
    return Rules(
        calendar=Calendar(tz=CCS, default=week),
        now=now,
        sla_by_area={AREA_1: 10, AREA_2: 15},
        reopen_window=timedelta(hours=48),
        abandon_after=timedelta(hours=24),
    )


def e(cid, kind, when, agent=None, area=AREA_1, **data):
    return Ev(cid, kind, when, agent, area, data)


SCENARIO = [
    # A: respuesta en 4 min (cumple), 60 min en espera, cierre → resolución 19 min hábiles
    e(1, T.CREATED, at(20, 9), area=None),
    e(1, T.BOT_ESCALATED, at(20, 9, 1), area_id=AREA_1),
    e(1, T.ACCEPTED, at(20, 9, 3), 7, from_status="queued"),
    e(1, T.AGENT_MESSAGE, at(20, 9, 5), 7, status="sent"),
    e(1, T.PENDING_STARTED, at(20, 9, 10), 7),
    e(1, T.PENDING_RESUMED, at(20, 10, 10), by="contact"),
    e(1, T.CLOSED, at(20, 10, 20), 7, by="agent", reason_id=1),
    # B: responde a los 20 min (incumple), se transfiere y lo cierra otro agente
    e(2, T.CREATED, at(20, 9, 30), area=None),
    e(2, T.BOT_ESCALATED, at(20, 9, 31), area_id=AREA_1),
    e(2, T.ACCEPTED, at(20, 9, 50), 8, from_status="queued"),
    e(2, T.AGENT_MESSAGE, at(20, 9, 50), 8, status="failed"),  # no cuenta
    e(2, T.AGENT_MESSAGE, at(20, 9, 51), 8, status="sent"),
    e(2, T.TRANSFERRED, at(20, 9, 55), 8, area=AREA_2, from_area_id=AREA_1, to_area_id=AREA_2),
    e(2, T.ACCEPTED, at(20, 10), 9, area=AREA_2, from_status="queued"),
    e(2, T.CLOSED, at(20, 10, 30), 9, area=AREA_2, by="agent", reason_id=2),
    # C: llega fuera de horario (21:01) y se responde 7:05 → 5 min hábiles; luego se reabre
    e(3, T.CREATED, at(20, 21), area=None),
    e(3, T.BOT_ESCALATED, at(20, 21, 1), area_id=AREA_1),
    e(3, T.ACCEPTED, at(21, 7), 7, from_status="queued"),
    e(3, T.AGENT_MESSAGE, at(21, 7, 5), 7, status="simulated"),
    e(3, T.CLOSED, at(21, 7, 30), 7, by="agent", reason_id=1),
    e(3, T.REOPENED, at(21, 12), by="contact", status="queued"),  # nuevo episodio el día 21
    # E: resuelta por el bot (contención)
    e(4, T.CREATED, at(20, 11), area=None),
    e(4, T.BOT_RESOLVED, at(20, 11, 5), area=None),
    e(4, T.CLOSED, at(20, 11, 5), area=None, by="bot", reason_id=None),
    # F: urgencia sin respuesta → abandono e incumplimiento
    e(5, T.CREATED, at(20, 12), area=None),
    e(5, T.URGENCY_DETECTED, at(20, 12), area=None),
    e(5, T.BOT_ESCALATED, at(20, 12), area_id=AREA_1),
    # G: cerrado sin respuesta humana → fuera del SLA
    e(6, T.CREATED, at(20, 13), area=None),
    e(6, T.BOT_ESCALATED, at(20, 13, 1), area_id=AREA_1),
    e(6, T.ACCEPTED, at(20, 13, 2), 7, from_status="queued"),
    e(6, T.CLOSED, at(20, 13, 10), 7, by="agent", reason_id=3),
]
NOW = at(23, 12)  # viernes: ventana de reapertura (48 h) ya vencida para los cierres del 20–21


def period_episodes(until: datetime = NOW):
    by_conv = defaultdict(list)
    for ev in SCENARIO:
        if ev.created_at <= until:
            by_conv[ev.conversation_id].append(ev)
    episodes, conversations = [], []
    for evs in by_conv.values():
        eps, facts = build_episodes(evs)
        episodes += [x for x in eps if at(20, 0) <= x.start < at(21, 0)]
        conversations.append(facts)
    return episodes, conversations


@pytest.fixture
def kpis():
    episodes, conversations = period_episodes()
    return summarize(episodes, conversations, [], urgent=1, rules=rules(NOW))


def test_volumes(kpis):
    assert kpis["conversations"] == 6
    assert kpis["episodes"] == 5  # A, B, C, F, G (el reabierto empieza el 21)
    assert kpis["urgent"] == 1


def test_first_response_in_business_minutes(kpis):
    assert kpis["first_response"] == {"count": 3, "avg": 9.7, "median": 5.0, "p90": 20.0}


def test_sla(kpis):
    # A cumple (4 ≤ 10), C cumple (5), B incumple (20), F incumple (sin respuesta), G se excluye
    assert kpis["sla"] == {"value": 0.5, "numerator": 2, "denominator": 4}


def test_resolution_time_discounts_pauses_and_off_hours(kpis):
    # A 79 − 60 de espera = 19 · B 59 · C 30 (solo 7:00–7:30) · G 9
    assert kpis["resolution_time"] == {"count": 4, "avg": 29.2, "median": 24.5, "p90": 59.0}
    assert kpis["resolution_rate"]["value"] == 0.8


def test_fcr_reopen_and_transfers(kpis):
    # A y G sí; B no (transferido); C no (reabierto dentro de 48 h)
    assert kpis["fcr"] == {"value": 0.5, "numerator": 2, "denominator": 4}
    assert kpis["reopen_rate"] == {"value": 0.25, "numerator": 1, "denominator": 4}
    assert kpis["transfer_rate"] == {"value": 0.2, "numerator": 1, "denominator": 5}


def test_abandon_and_bot_containment(kpis):
    assert kpis["abandon_rate"] == {"value": 0.2, "numerator": 1, "denominator": 5}
    assert kpis["bot_containment"] == {"value": 0.1667, "numerator": 1, "denominator": 6}


def test_fcr_is_pending_until_reopen_window_passes():
    now = at(20, 14)
    episodes, conversations = period_episodes(until=now)
    early = summarize(episodes, conversations, [], 0, rules(now))
    # A las 14:00 del 20 solo se sabe que B no es FCR (se transfirió); A y G esperan la ventana
    assert early["fcr"] == {"value": 0.0, "numerator": 0, "denominator": 1}
    # F lleva 2 h en cola: incumple el SLA, pero aún no cuenta como abandono (24 h)
    assert early["abandon_rate"]["numerator"] == 0
    assert early["sla"] == {"value": 0.3333, "numerator": 1, "denominator": 3}  # A sí; B y F no


def test_agent_reopen_and_supervisor_intervention():
    events = [
        e(9, T.CREATED, at(20, 9), area=None),
        e(9, T.ACCEPTED, at(20, 9, 2), 5, from_status="bot"),  # supervisor interviene
        e(9, T.AGENT_MESSAGE, at(20, 9, 3), 5, status="sent"),
        e(9, T.CLOSED, at(20, 9, 10), 5, by="agent", reason_id=1),
        e(9, T.REOPENED, at(20, 15), 5, by="agent", status="open"),
        e(9, T.AGENT_MESSAGE, at(20, 15, 1), 5, status="sent"),
        e(9, T.CLOSED, at(20, 15, 5), 5, by="agent", reason_id=1),
    ]
    episodes, _ = build_episodes(events)
    assert [x.origin for x in episodes] == ["intervention", "agent_reopen"]
    kpis = summarize(episodes, [], [], 0, rules(NOW))
    assert kpis["first_response"]["count"] == 1  # el reabierto por el agente no tiene 1ª respuesta
    assert kpis["first_response"]["median"] == 1.0
    assert kpis["reopen_rate"]["numerator"] == 1


def test_by_agent_attribution():
    episodes, _ = period_episodes()
    rows = {r["agent_id"]: r for r in by_agent_from(episodes)}
    assert rows[7]["accepted"] == 3 and rows[7]["closed"] == 3  # A, C, G
    assert rows[7]["first_response"]["count"] == 2  # A y C
    assert rows[7]["fcr"] == {"value": 0.6667, "numerator": 2, "denominator": 3}
    assert rows[8]["accepted"] == 1 and rows[8]["closed"] == 0  # B: respondió y transfirió
    assert rows[9]["closed"] == 1 and rows[9]["accepted"] == 0


def by_agent_from(episodes):
    class Data:
        pass

    data = Data()
    data.episodes, data.surveys, data.rules = episodes, [], rules(NOW)
    return by_agent(data, {})


def survey(kind, score, status=SurveyStatus.ANSWERED):
    return SurveyRow(kind, status, score, at(20, 9), at(20, 10), 7, AREA_1)


def test_csat_and_nps_formulas():
    csat = csat_summary(
        [survey(SurveyKind.CSAT, s) for s in (5, 4, 3, 1)]
        + [survey(SurveyKind.CSAT, None, SurveyStatus.SENT)]
        + [survey(SurveyKind.CSAT, None, SurveyStatus.FAILED)]
    )
    assert csat["avg"] == 3.25
    assert csat["satisfied"] == {"value": 0.5, "numerator": 2, "denominator": 4}
    assert csat["response_rate"] == {"value": 0.8, "numerator": 4, "denominator": 5}

    nps = nps_summary([survey(SurveyKind.NPS, s) for s in (10, 9, 9, 8, 7, 6, 3, 0, 10, 5)])
    assert nps == {
        "responses": 10,
        "promoters": 4,
        "passives": 2,
        "detractors": 4,
        "score": 0.0,
    }
