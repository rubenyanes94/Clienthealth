"""Cada fórmula de docs/METRICAS.md (módulo de Casos), con escenarios de eventos fijos."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.models.enums import CaseEventType as T
from app.models.enums import Priority
from app.services.business_time import Calendar
from app.services.case_metrics import (
    CasePeriod,
    Ev,
    attention_minutes,
    build_facts,
    by_agent,
    by_area,
    goal_status,
    overview,
    reasons,
    resolution_minutes,
    time_to_attention,
    waiting_minutes,
)
from app.services.metrics import make_period

T0 = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)  # 11:00 en Caracas
CLOCK = Calendar(tz=ZoneInfo("America/Caracas"))  # sin horario: minutos de reloj
LAB, SEGUROS = 2, 4
ANA, LUIS = 7, 8


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def created(area=LAB, minutes=0, agent=ANA) -> Ev:
    return Ev(T.CREATED, at(minutes), agent, area, {"area_id": area})


def step(minutes, old, new, agent=ANA, area=LAB) -> Ev:
    return Ev(T.STAGE_CHANGED, at(minutes), agent, area, {"from": old, "to": new})


def moved(minutes, to, frm=LAB, agent=ANA) -> Ev:
    return Ev(
        T.TRANSFERRED,
        at(minutes),
        agent,
        to,
        {"from_area_id": frm, "to_area_id": to, "from_stage": "in_progress"},
    )


def period_of(*cases, area=None, goal=15, now_minutes=1000) -> CasePeriod:
    facts = [build_facts(i, evs) for i, evs in enumerate(cases, start=1)]
    return CasePeriod(
        make_period(date(2026, 10, 20), date(2026, 10, 20)),
        CLOCK,
        goal,
        at(now_minutes),
        area,
        facts,
    )


SIMPLE = [
    created(),
    step(10, "registered", "in_progress"),
    step(40, "in_progress", "waiting"),
    step(60, "waiting", "in_progress"),
    step(70, "in_progress", "resolved"),
    step(80, "resolved", "closed"),
]


def test_times_of_a_simple_case():
    facts = build_facts(1, SIMPLE)
    stay = facts.stays[0]
    assert time_to_attention(stay, CLOCK) == 10
    assert attention_minutes(stay, CLOCK) == 40  # 30 + 10
    assert waiting_minutes(stay, CLOCK) == 20
    assert resolution_minutes(facts, CLOCK) == 50  # 10 por atender + 40 en atención
    assert facts.resolved and facts.was_closed and not facts.was_reopened


def test_case_that_never_waited_does_not_count_as_waiting():
    stay = build_facts(
        1, [created(), step(5, "registered", "in_progress"), step(9, "in_progress", "resolved")]
    ).stays[0]
    assert waiting_minutes(stay, CLOCK) is None
    assert attention_minutes(stay, CLOCK) == 4


def test_case_in_progress_has_no_final_times():
    facts = build_facts(1, [created(), step(10, "registered", "in_progress")])
    assert attention_minutes(facts.stays[0], CLOCK) is None
    assert resolution_minutes(facts, CLOCK) is None


def test_goal_status():
    def status(minutes, now=100, goal=15):
        evs = [created()]
        if minutes is not None:
            evs.append(step(minutes, "registered", "in_progress"))
        return goal_status(build_facts(1, evs).stays[0], CLOCK, goal, at(now))

    assert status(15) == "met"  # justo en la meta
    assert status(16) == "missed"
    assert status(None, now=10) is None  # sin atender, aún dentro de la meta
    assert status(None, now=20) == "missed"


def test_each_area_answers_for_its_own_time():
    facts = build_facts(
        1,
        [
            created(),
            step(5, "registered", "in_progress"),
            moved(25, SEGUROS),
            step(45, "registered", "in_progress", area=SEGUROS),
            step(55, "in_progress", "resolved", area=SEGUROS),
        ],
    )
    lab, seguros = facts.stays
    assert (time_to_attention(lab, CLOCK), attention_minutes(lab, CLOCK)) == (5, 20)
    assert (time_to_attention(seguros, CLOCK), attention_minutes(seguros, CLOCK)) == (20, 10)
    assert facts.transferred
    assert resolution_minutes(facts, CLOCK) == 55


def test_transfer_without_attention_counts_against_goal_only_if_late():
    quick = build_facts(1, [created(), moved(5, SEGUROS)]).stays[0]
    slow = build_facts(1, [created(), moved(30, SEGUROS)]).stays[0]
    assert goal_status(quick, CLOCK, 15, at(100)) is None
    assert goal_status(slow, CLOCK, 15, at(100)) == "missed"
    assert attention_minutes(slow, CLOCK) is None


def test_reopening_does_not_count_time_while_closed():
    facts = build_facts(
        1,
        [
            created(),
            step(10, "registered", "in_progress"),
            step(20, "in_progress", "resolved"),
            step(30, "resolved", "closed"),
            step(500, "closed", "in_progress"),
            step(510, "in_progress", "resolved"),
        ],
    )
    assert facts.was_reopened
    assert resolution_minutes(facts, CLOCK) == 30  # 10 + 10 + 10


def test_business_hours_are_used():
    # De 9 a 17 (Caracas). Entra a las 16:50 y se atiende a las 9:10 del día siguiente.
    calendar = Calendar(
        tz=ZoneInfo("America/Caracas"), default={1: [(time(9), time(17))], 2: [(time(9), time(17))]}
    )
    start = datetime(2026, 10, 20, 20, 50, tzinfo=UTC)
    evs = [
        Ev(T.CREATED, start, ANA, LAB, {"area_id": LAB}),
        Ev(
            T.STAGE_CHANGED,
            datetime(2026, 10, 21, 13, 10, tzinfo=UTC),
            ANA,
            LAB,
            {"from": "registered", "to": "in_progress"},
        ),
    ]
    assert time_to_attention(build_facts(1, evs).stays[0], calendar) == 20


def test_overview():
    late = [created(minutes=1), step(40, "registered", "in_progress")]
    moved_case = [
        created(minutes=2),
        step(7, "registered", "in_progress"),
        moved(27, SEGUROS),
        step(32, "registered", "in_progress", area=SEGUROS),
        step(42, "in_progress", "resolved", area=SEGUROS),
    ]
    data = overview(period_of(SIMPLE, late, moved_case))
    assert data["created"] == 3
    assert data["received"] == 4  # una entrada más por la transferencia
    assert data["closed"] == 1
    assert data["goal"]["numerator"] == 3 and data["goal"]["denominator"] == 4
    assert data["goal_minutes"] == 15
    assert data["time_to_attention"]["count"] == 4
    assert data["resolution_rate"]["numerator"] == 2
    assert data["transfer_rate"]["numerator"] == 1
    assert data["reopen_rate"] == {"value": 0.0, "numerator": 0, "denominator": 1}


def test_overview_with_area_filter():
    transferred = [
        created(),
        step(5, "registered", "in_progress"),
        moved(10, SEGUROS),
    ]
    data = overview(period_of(transferred, SIMPLE, area=SEGUROS))
    assert data["created"] == 1  # el que pasó por Seguros
    assert data["received"] == 1
    assert data["closed"] == 0
    # Sin atender en Seguros y lleva más de la meta.
    assert data["goal"]["denominator"] == 1 and data["goal"]["numerator"] == 0


def test_empty_period_has_null_values():
    data = overview(period_of())
    assert data["created"] == 0
    assert data["goal"]["value"] is None
    assert data["time_to_attention"]["median"] is None


def test_by_area():
    rows = by_area(
        period_of(
            [created(), step(5, "registered", "in_progress"), moved(10, SEGUROS)],
            SIMPLE,
        ),
        {LAB: "Laboratorio", SEGUROS: "Seguros"},
    )
    assert [r["name"] for r in rows] == ["Laboratorio", "Seguros"]
    assert rows[0]["received"] == 2 and rows[0]["closed"] == 1
    assert rows[1]["received"] == 1 and rows[1]["closed"] == 0


def test_by_agent_credits_who_did_each_thing():
    case = [
        created(agent=ANA),
        step(5, "registered", "in_progress", agent=ANA),
        step(25, "in_progress", "waiting", agent=ANA),
        step(30, "waiting", "in_progress", agent=LUIS),
        step(40, "in_progress", "resolved", agent=LUIS),
        step(50, "resolved", "closed", agent=ANA),
    ]
    rows = {r["name"]: r for r in by_agent(period_of(case), {ANA: "Ana", LUIS: "Luis"})}
    assert rows["Ana"]["attended"] == 1 and rows["Ana"]["closed"] == 1
    assert rows["Ana"]["resolved"] == 0 and rows["Ana"]["attention_time"]["median"] == 20
    assert rows["Luis"]["attended"] == 0 and rows["Luis"]["resolved"] == 1
    assert rows["Luis"]["attention_time"]["median"] == 10


def test_reasons_use_the_closing_date():
    data = period_of(SIMPLE)
    data.facts[0].reason_id = 3
    data.facts[0].priority = Priority.HIGH
    assert reasons(data, {3: "Facturación"}) == [
        {"reason_id": 3, "name": "Facturación", "count": 1, "share": 1.0}
    ]
    assert overview(data)["urgent"] == 1
