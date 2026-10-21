from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.base import utcnow
from app.models import Conversation
from app.models.enums import AgentRole
from tests.conftest import area_id, login, make_agent, patient_says, reason_id


def today() -> str:
    return utcnow().astimezone(ZoneInfo("America/Caracas")).date().isoformat()


def params(**extra):
    return {"from": today(), "to": today(), **extra}


def handled_case(anon, db, agent):
    patient_says(anon, "Hola")
    patient_says(anon, "2")
    cid = db.scalar(select(Conversation.id))
    agent.post(f"/api/conversations/{cid}/accept")
    agent.post(f"/api/conversations/{cid}/messages", json={"body": "Buenos días"})
    agent.post(f"/api/conversations/{cid}/close", json={"contact_reason_id": reason_id(db)})
    patient_says(anon, "5")  # CSAT
    patient_says(anon, "Hola", wa_id="584140000077")  # otra conversación, queda en el bot


def test_metrics_require_supervisor(lab_agent):
    assert lab_agent.get("/api/metrics/overview", params=params()).status_code == 403


def test_overview_from_real_flow(anon, db, lab_agent, supervisor):
    handled_case(anon, db, lab_agent)
    data = supervisor.get("/api/metrics/overview", params=params()).json()
    assert data["conversations"] == 2
    assert data["episodes"] == 1
    assert data["first_response"]["count"] == 1
    assert data["sla"]["value"] == 1.0
    assert data["resolution_rate"]["value"] == 1.0
    assert data["csat"]["responses"] == 1 and data["csat"]["avg"] == 5
    assert data["bot_containment"]["denominator"] == 2

    lab = supervisor.get(
        "/api/metrics/overview", params=params(area_id=area_id(db, "laboratorio"))
    ).json()
    assert lab["episodes"] == 1 and lab["csat"]["responses"] == 1
    other = supervisor.get(
        "/api/metrics/overview", params=params(area_id=area_id(db, "imagenologia"))
    ).json()
    assert other["episodes"] == 0 and other["sla"]["value"] is None


def test_breakdowns(anon, db, lab_agent, supervisor):
    handled_case(anon, db, lab_agent)
    hours = supervisor.get("/api/metrics/by-hour", params=params()).json()
    assert len(hours) == 24
    assert sum(h["inbound_messages"] for h in hours) == 4
    assert sum(h["episodes"] for h in hours) == 1

    areas = supervisor.get("/api/metrics/by-area", params=params()).json()
    assert [a["name"] for a in areas] == ["Laboratorio"]

    agents = supervisor.get("/api/metrics/by-agent", params=params()).json()
    assert agents[0]["name"] == "Lab" and agents[0]["closed"] == 1
    assert agents[0]["csat"]["avg"] == 5

    reasons = supervisor.get("/api/metrics/reasons", params=params()).json()
    assert reasons == [
        {"reason_id": reason_id(db), "name": "Información general", "count": 1, "share": 1.0}
    ]
    daily = supervisor.get("/api/metrics/csat-daily", params=params()).json()
    assert daily == [{"day": today(), "responses": 1, "avg": 5.0, "satisfied": 1.0}]


def test_period_validation(supervisor):
    bad = supervisor.get("/api/metrics/overview", params={"from": "2026-10-10", "to": "2026-10-01"})
    assert bad.status_code == 422
    long = supervisor.get(
        "/api/metrics/overview", params={"from": "2024-01-01", "to": "2026-01-01"}
    )
    assert long.status_code == 422


def test_calendar_admin(db):
    make_agent(db, "admin@example.com", AgentRole.ADMIN)
    admin = login("admin@example.com")
    default = admin.get("/api/admin/business-hours").json()
    assert len(default["slots"]) == 6 and not default["inherits_default"]

    lab = area_id(db, "laboratorio")
    assert admin.get("/api/admin/business-hours", params={"area_id": lab}).json()[
        "inherits_default"
    ]
    saved = admin.put(
        "/api/admin/business-hours",
        params={"area_id": lab},
        json={"slots": [{"weekday": 6, "opens_at": "08:00", "closes_at": "12:00"}]},
    )
    assert saved.status_code == 200 and saved.json()["slots"][0]["weekday"] == 6
    invalid = admin.put(
        "/api/admin/business-hours",
        json={"slots": [{"weekday": 1, "opens_at": "12:00", "closes_at": "08:00"}]},
    )
    assert invalid.status_code == 422

    created = admin.post("/api/admin/holidays", json={"day": "2026-12-31", "name": "Fin de año"})
    assert created.status_code == 201
    duplicate = admin.post("/api/admin/holidays", json={"day": "2026-12-31", "name": "Otra vez"})
    assert duplicate.status_code == 409
    assert admin.delete(f"/api/admin/holidays/{created.json()['id']}").status_code == 204
