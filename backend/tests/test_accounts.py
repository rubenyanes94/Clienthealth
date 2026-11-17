"""Cuentas por invitación: el administrador crea la cuenta y la persona crea su contraseña."""

import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core.config import get_settings
from app.db.base import utcnow
from app.main import app
from app.models import AccountToken, Agent
from app.models.enums import AgentRole
from app.services import email
from tests.conftest import PASSWORD, login, make_agent

NEW_PASSWORD = "una-clave-propia-123"


@pytest.fixture
def outbox(monkeypatch):
    """Captura los correos en vez de enviarlos."""
    sent: list[dict] = []

    def fake_send(to, subject, text, html):
        sent.append({"to": to, "subject": subject, "text": text, "html": html})
        return email.EmailResult(sent=True)

    monkeypatch.setattr(email, "send", fake_send)
    return sent


@pytest.fixture
def admin(db) -> TestClient:
    make_agent(db, "admin@example.com", AgentRole.ADMIN)
    return login("admin@example.com")


def token_from(message: dict) -> str:
    return re.search(r"#token=([\w-]+)", message["text"]).group(1)


def invite(admin, address="nueva@example.com"):
    body = {"name": "Nueva Persona", "email": address, "role": "agent"}
    response = admin.post("/api/admin/agents", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def fresh() -> TestClient:
    return TestClient(app, base_url="https://testserver")


def test_admin_invites_and_the_person_creates_the_password(admin, outbox):
    created = invite(admin, "Nueva@EXAMPLE.com")
    assert created["agent"]["email"] == "nueva@example.com"
    assert created["agent"]["password_set_at"] is None  # invitación pendiente
    assert created["access"] == {
        "email_sent": True,
        "dry_run": False,
        "error": None,
        "link_path": None,
    }
    [message] = outbox
    assert message["to"] == "nueva@example.com"
    assert message["subject"] == "Active su cuenta de Atención al Paciente"
    assert "Nueva" in message["text"] and "72 horas" in message["text"]
    token = token_from(message)

    # Sin contraseña todavía, nadie puede entrar.
    for password in ("", "cualquier-cosa-123", PASSWORD):
        attempt = fresh().post(
            "/api/auth/login", json={"email": "nueva@example.com", "password": password or "x"}
        )
        assert attempt.status_code == 401

    client = fresh()
    check = client.post("/api/auth/password-reset/verify", json={"token": token}).json()
    assert check == {"purpose": "invite", "name": "Nueva Persona", "email": "nueva@example.com"}
    short = {"token": token, "new_password": "corta"}
    assert client.post("/api/auth/password-reset/confirm", json=short).status_code == 422
    done = client.post(
        "/api/auth/password-reset/confirm", json={"token": token, "new_password": NEW_PASSWORD}
    )
    assert done.status_code == 200
    assert done.json()["email"] == "nueva@example.com"
    assert client.get("/api/auth/me").status_code == 200  # queda con la sesión iniciada

    login_ok = fresh().post(
        "/api/auth/login", json={"email": "nueva@example.com", "password": NEW_PASSWORD}
    )
    assert login_ok.status_code == 200
    again = {"token": token, "new_password": "otra-clave-12345"}
    assert fresh().post("/api/auth/password-reset/confirm", json=again).status_code == 400
    users = {u["email"]: u for u in admin.get("/api/admin/agents").json()}
    assert users["nueva@example.com"]["password_set_at"] is not None


def test_only_the_hash_of_the_link_is_stored(admin, outbox, db):
    invite(admin)
    token = token_from(outbox[0])
    stored = db.scalar(select(AccountToken.token_hash))
    assert stored != token and len(stored) == 64 and token not in stored


def test_resending_invalidates_the_previous_link(admin, outbox, db):
    agent_id = invite(admin)["agent"]["id"]
    first = token_from(outbox[0])
    resent = admin.post(f"/api/admin/agents/{agent_id}/send-access")
    assert resent.status_code == 200 and resent.json()["email_sent"] is True
    second = token_from(outbox[1])
    verify = fresh().post("/api/auth/password-reset/verify", json={"token": first})
    assert verify.status_code == 400
    assert (
        fresh().post("/api/auth/password-reset/verify", json={"token": second}).status_code == 200
    )


def test_expired_link_is_rejected(admin, outbox, db):
    invite(admin)
    db.execute(update(AccountToken).values(expires_at=utcnow() - timedelta(minutes=1)))
    db.commit()
    response = fresh().post(
        "/api/auth/password-reset/verify", json={"token": token_from(outbox[0])}
    )
    assert response.status_code == 400
    assert "venció" in response.json()["detail"]


def test_inactive_accounts_get_no_links(admin, outbox, db):
    agent_id = invite(admin)["agent"]["id"]
    token = token_from(outbox[0])
    db.execute(update(Agent).where(Agent.id == agent_id).values(is_active=False))
    db.commit()
    assert fresh().post("/api/auth/password-reset/verify", json={"token": token}).status_code == 400
    assert admin.post(f"/api/admin/agents/{agent_id}/send-access").status_code == 409
    fresh().post("/api/auth/password-reset/request", json={"email": "nueva@example.com"})
    assert len(outbox) == 1


def test_forgot_password_never_reveals_whether_the_email_exists(db, outbox, lab_agent):
    unknown = fresh().post("/api/auth/password-reset/request", json={"email": "nadie@example.com"})
    known = fresh().post("/api/auth/password-reset/request", json={"email": "LAB@example.com"})
    assert unknown.status_code == known.status_code == 204
    assert unknown.content == known.content == b""
    [message] = outbox
    assert message["to"] == "lab@example.com"
    assert message["subject"].startswith("Restablezca")
    # Pulsar muchas veces no llena la bandeja.
    fresh().post("/api/auth/password-reset/request", json={"email": "lab@example.com"})
    assert len(outbox) == 1


def test_reset_closes_every_other_session(db, outbox, lab_agent):
    assert lab_agent.get("/api/auth/me").status_code == 200
    fresh().post("/api/auth/password-reset/request", json={"email": "lab@example.com"})
    token = token_from(outbox[0])
    client = fresh()
    confirm = {"token": token, "new_password": NEW_PASSWORD}
    assert client.post("/api/auth/password-reset/confirm", json=confirm).status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    assert lab_agent.get("/api/auth/me").status_code == 401  # la sesión vieja ya no vale


def test_changing_the_password_keeps_this_session_and_closes_the_rest(db, lab_agent):
    other_device = login("lab@example.com")
    change = {"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    assert lab_agent.post("/api/auth/password", json=change).status_code == 204
    assert lab_agent.get("/api/auth/me").status_code == 200
    assert other_device.get("/api/auth/me").status_code == 401


def test_without_smtp_the_link_is_shown_only_outside_production(admin, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "")
    access = invite(admin)["access"]
    assert access["email_sent"] is False and access["dry_run"] is True
    assert access["link_path"].startswith("/restablecer#token=")

    monkeypatch.setattr(settings, "environment", "production")
    access = invite(admin, "otra@example.com")["access"]
    assert access["link_path"] is None
    assert "SMTP_HOST" in access["error"]


def test_smtp_failure_is_reported_and_can_be_retried(admin, monkeypatch):
    monkeypatch.setattr(
        email, "send", lambda *a: email.EmailResult(sent=False, error="El servidor no respondió")
    )
    access = invite(admin)["access"]
    assert access["email_sent"] is False and access["error"] == "El servidor no respondió"
    assert access["link_path"] is None  # hubo servidor: no es modo de pruebas


def test_only_admins_invite_or_resend(lab_agent, supervisor, admin, outbox):
    agent_id = invite(admin)["agent"]["id"]
    body = {"name": "X", "email": "x@example.com"}
    for client in (lab_agent, supervisor):
        assert client.post("/api/admin/agents", json=body).status_code == 403
        assert client.post(f"/api/admin/agents/{agent_id}/send-access").status_code == 403


def test_admin_can_still_set_a_password_through_the_api(admin, outbox):
    body = {"name": "Con Clave", "email": "clave@example.com", "password": "clave-segura-456"}
    created = admin.post("/api/admin/agents", json=body).json()
    assert created["access"] is None and outbox == []
    assert created["agent"]["password_set_at"] is not None


def test_smtp_uses_starttls_login_and_sends_text_and_html(monkeypatch):
    calls: list = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login", user))

        def send_message(self, message):
            calls.append(("send", message["To"], message["Subject"], message.get_content_type()))

    settings = get_settings()
    monkeypatch.setattr(settings, "smtp_host", "smtp.ejemplo.com")
    monkeypatch.setattr(settings, "smtp_user", "usuario")
    monkeypatch.setattr(settings, "smtp_password", "secreto")
    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)
    result = email.send("ana@example.com", "Asunto", "texto", "<p>html</p>")
    assert result == email.EmailResult(sent=True)
    assert calls == [
        ("connect", "smtp.ejemplo.com", 587, 10),
        ("starttls",),
        ("login", "usuario"),
        ("send", "ana@example.com", "Asunto", "multipart/alternative"),
    ]


def test_smtp_errors_do_not_leak_details(monkeypatch):
    class Broken:
        def __init__(self, *a, **k):
            raise OSError("Connection refused to 10.0.0.5")

    monkeypatch.setattr(get_settings(), "smtp_host", "smtp.ejemplo.com")
    monkeypatch.setattr(email.smtplib, "SMTP", Broken)
    result = email.send("ana@example.com", "Asunto", "texto", "<p>html</p>")
    assert result.sent is False and result.error == "El servidor de correo no aceptó el envío"
