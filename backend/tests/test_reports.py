"""Informe PDF de indicadores: análisis en lenguaje sencillo y descarga."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.db.base import utcnow
from app.models import Contact, Conversation, Survey
from app.models.enums import AgentRole, SurveyKind, SurveyStatus
from app.services import report_analysis as an
from app.services.report_pdf import period_label, previous_period
from tests.conftest import login, make_agent, patient_says

# --- Formato y variaciones ----------------------------------------------------------------------


def test_spanish_number_formats():
    assert an.number(1234.5, 1) == "1.234,5"
    assert an.percent(0.846) == "85 %"
    assert an.minutes(0.4) == "menos de 1 min"
    assert an.minutes(42) == "42 min"
    assert an.minutes(125) == "2 h 5 min"
    assert an.minutes(120) == "2 h"
    assert an.number(None) == an.percent(None) == an.minutes(None) == "—"


@pytest.mark.parametrize(
    ("args", "text", "tone"),
    [
        ((0.9, 0.85, "ratio", True), "5 puntos más que el período anterior", "good"),
        ((0.8, 0.85, "ratio", True), "5 puntos menos que el período anterior", "bad"),
        ((12, 8, "minutes", False), "4 min más que el período anterior", "bad"),
        ((6, 8, "minutes", False), "2 min menos que el período anterior", "good"),
        ((40, 32, "points", True), "8 puntos más que el período anterior", "good"),
        ((0.85, 0.852, "ratio", True), "igual que el período anterior", "neutral"),
        ((None, 0.8, "ratio", True), "sin dato del período anterior para comparar", "neutral"),
        ((120, 100, "count", True), "20 (20 %) más que el período anterior", "good"),
        ((143, 1, "count", True), "142 más que el período anterior", "good"),
    ],
)
def test_change(args, text, tone):
    current, previous, kind, better = args
    assert an.change(current, previous, kind=kind, higher_is_better=better) == (text, tone)


def test_nps_interpretation():
    nps = {"responses": 50, "promoters": 30, "passives": 10, "detractors": 10, "score": 40.0}
    [finding] = an.nps(nps, {**nps, "score": 32.0})
    assert finding.tone == "good"
    assert "El NPS fue 40, un nivel bueno" in finding.text
    assert "60 % de los pacientes nos recomendaría" in finding.text
    assert "8 puntos más que el período anterior" in finding.text

    low = {"responses": 10, "promoters": 2, "passives": 2, "detractors": 6, "score": -40.0}
    findings = an.nps(low, None)
    assert findings[0].tone == "bad" and "crítico" in findings[0].text
    assert findings[1].tone == "warn" and "Solo 10 respuestas" in findings[1].text

    none = {"responses": 0, "promoters": 0, "passives": 0, "detractors": 0, "score": None}
    assert an.nps(none, None)[0].text == "No hubo respuestas de NPS en el período."


@pytest.mark.parametrize(
    ("score", "label"), [(75, "excelente"), (30, "bueno"), (0, "por mejorar"), (-1, "crítico")]
)
def test_nps_bands(score, label):
    nps = {"responses": 100, "promoters": 50, "passives": 25, "detractors": 25, "score": score}
    assert label in an.nps(nps, None)[0].text


def test_case_findings_point_out_the_weakest_area():
    overview = {
        "received": 40,
        "created": 30,
        "closed": 25,
        "goal": {"value": 0.8},
        "goal_minutes": 15,
        "time_to_attention": {"median": 6.0},
    }
    areas = [
        {"name": "Laboratorio", "received": 20, "goal": {"value": 0.95}},
        {"name": "Seguros", "received": 12, "goal": {"value": 0.6}},
        {"name": "Hospitalización", "received": 2, "goal": {"value": 0.1}},  # muy pocos: no cuenta
    ]
    texts = [f.text for f in an.cases(overview, None, areas)]
    assert any("Seguros es el área con menos casos atendidos a tiempo (60 %)" in t for t in texts)
    assert not any("Hospitalización" in t for t in texts)


def test_highlights_put_problems_first():
    findings = [
        an.Finding("x", "bien", "good"),
        an.Finding("x", "dato", "neutral"),
        an.Finding("x", "grave", "bad"),
        an.Finding("x", "ojo", "warn"),
    ]
    assert [f.text for f in an.highlights([findings])] == ["grave", "ojo", "bien", "dato"]


def test_period_labels():
    assert period_label(date(2026, 11, 1), date(2026, 11, 30)) == "1 al 30 de noviembre de 2026"
    assert (
        period_label(date(2026, 10, 28), date(2026, 11, 3))
        == "28 de octubre al 3 de noviembre de 2026"
    )
    assert period_label(date(2026, 12, 29), date(2027, 1, 4)) == (
        "29 de diciembre de 2026 al 4 de enero de 2027"
    )
    assert previous_period(date(2026, 11, 1), date(2026, 11, 30)) == (
        date(2026, 10, 2),
        date(2026, 10, 31),
    )


# --- Descarga -----------------------------------------------------------------------------------


def params(**extra):
    today = utcnow().date()
    return {"from": (today - timedelta(days=6)).isoformat(), "to": today.isoformat(), **extra}


def test_downloads_a_pdf(db, supervisor, anon):
    patient_says(anon, "Hola")
    patient_says(anon, "2")
    conversation = db.scalar(select(Conversation))
    contact = db.scalar(select(Contact))
    for score in (10, 9, 9, 7, 3):
        db.add(
            Survey(
                conversation_id=conversation.id,
                contact_id=contact.id,
                kind=SurveyKind.NPS,
                status=SurveyStatus.ANSWERED,
                score=score,
                sent_at=utcnow() - timedelta(hours=2),
                answered_at=utcnow() - timedelta(hours=1),
            )
        )
    db.commit()
    response = supervisor.get("/api/reports/indicators.pdf", params=params())
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('.pdf"')


def test_empty_period_still_produces_a_report(supervisor):
    response = supervisor.get(
        "/api/reports/indicators.pdf", params={"from": "2020-01-01", "to": "2020-01-31"}
    )
    assert response.status_code == 200 and response.content.startswith(b"%PDF")


def test_area_filter_and_validation(db, supervisor):
    from tests.conftest import area_id

    ok = supervisor.get(
        "/api/reports/indicators.pdf", params=params(area_id=area_id(db, "laboratorio"))
    )
    assert ok.status_code == 200
    backwards = {"from": "2026-11-10", "to": "2026-11-01"}
    assert supervisor.get("/api/reports/indicators.pdf", params=backwards).status_code == 422
    too_long = {"from": "2024-01-01", "to": "2026-01-01"}
    assert supervisor.get("/api/reports/indicators.pdf", params=too_long).status_code == 422


def test_only_supervisors_and_admins(db, lab_agent):
    assert lab_agent.get("/api/reports/indicators.pdf", params=params()).status_code == 403
    make_agent(db, "admin@cm.test", AgentRole.ADMIN)
    assert (
        login("admin@cm.test").get("/api/reports/indicators.pdf", params=params()).status_code
        == 200
    )
