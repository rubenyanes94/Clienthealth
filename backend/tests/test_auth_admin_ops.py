from datetime import timedelta

from sqlalchemy import func, select, update

from app.db.base import utcnow
from app.models import Conversation, ConversationEvent
from app.models.enums import AgentRole, EventType
from tests.conftest import login, make_agent, patient_says


def test_login_sets_httponly_cookie_and_logout(db, anon):
    make_agent(db, "ana@example.com")
    bad = anon.post("/api/auth/login", json={"email": "ana@example.com", "password": "x"})
    assert bad.status_code == 401

    response = anon.post(
        "/api/auth/login", json={"email": "ANA@example.com", "password": "clave-segura-123"}
    )
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "secure" in cookie and "samesite=strict" in cookie
    assert anon.get("/api/auth/me").json()["email"] == "ana@example.com"

    anon.post("/api/auth/logout")
    assert anon.get("/api/auth/me").status_code == 401


def test_requires_session(anon):
    assert anon.get("/api/inbox").status_code == 401


def test_roles_are_enforced_on_admin(db, lab_agent):
    assert lab_agent.get("/api/admin/areas").status_code == 403
    assert lab_agent.get("/api/catalog").status_code == 200

    make_agent(db, "admin@example.com", AgentRole.ADMIN)
    admin = login("admin@example.com")
    created = admin.post(
        "/api/admin/areas",
        json={"name": "Odontología", "slug": "odontologia", "is_default": True},
    )
    assert created.status_code == 201
    defaults = [a for a in admin.get("/api/admin/areas").json() if a["is_default"]]
    assert [a["slug"] for a in defaults] == ["odontologia"]

    duplicate = admin.post("/api/admin/areas", json={"name": "Odontología", "slug": "odonto"})
    assert duplicate.status_code == 409

    agent = admin.post(
        "/api/admin/agents",
        json={"name": "Luis", "email": "luis@example.com", "password": "otra-clave-123"},
    )
    assert agent.status_code == 201
    assert "password_hash" not in agent.json()


def test_cron_requires_secret_and_is_idempotent(anon, db):
    patient_says(anon, "Hola")
    patient_says(anon, "2")
    db.execute(update(Conversation).values(queued_at=utcnow() - timedelta(hours=30)))
    db.commit()

    assert anon.get("/api/cron/daily-rollup").status_code == 401
    headers = {"Authorization": "Bearer test-cron-secret"}
    assert anon.get("/api/cron/daily-rollup", headers=headers).json() == {
        "abandoned_marked": 1,
        "nps_sent": 0,
    }
    assert anon.get("/api/cron/daily-rollup", headers=headers).json() == {
        "abandoned_marked": 0,
        "nps_sent": 0,
    }
    count = db.scalar(
        select(func.count())
        .select_from(ConversationEvent)
        .where(ConversationEvent.type == EventType.ABANDONED)
    )
    assert count == 1


def test_live_metrics_and_simulator(db, supervisor, lab_agent):
    response = supervisor.post("/api/dev/simulate-inbound", json={"text": "tengo dolor de pecho"})
    assert response.status_code == 202
    assert lab_agent.post("/api/dev/simulate-inbound", json={"text": "hola"}).status_code == 403

    live = supervisor.get("/api/metrics/live").json()
    assert live["queued"] == 1
    assert live["urgent_queued"] == 1
    assert live["agents_online"] == 2
