"""Permisología: lo que puede y no puede hacer cada rol (matriz en app/core/permissions.py)."""

import re

import pytest
from fastapi.routing import APIRoute

from app.core.permissions import ROLE_PERMISSIONS, Permission
from app.main import app
from app.models.enums import AgentRole
from tests.conftest import area_id, login, make_agent, patient_says
from tests.test_patients_cases import new_case, new_patient, new_task, to_stage

# Rutas que no exigen sesión, y por qué.
PUBLIC = {
    ("GET", "/api/health"),  # monitoreo
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/logout"),
    ("POST", "/api/auth/password-reset/request"),  # «¿Olvidó su contraseña?»
    ("POST", "/api/auth/password-reset/verify"),  # el enlace del correo es la credencial
    ("POST", "/api/auth/password-reset/confirm"),
    ("GET", "/api/webhooks/whatsapp"),  # verificación de Meta (token propio)
    ("POST", "/api/webhooks/whatsapp"),  # Meta (firma propia)
    ("GET", "/api/cron/daily-rollup"),  # Vercel Cron (secreto propio)
    ("POST", "/api/cron/daily-rollup"),
}


def api_routes():
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path.startswith("/api"):
            for method in route.methods:
                yield method, route.path


def test_every_route_requires_a_session_unless_listed_as_public(anon):
    unprotected = []
    for method, path in api_routes():
        if (method, path) in PUBLIC:
            continue
        url = re.sub(r"\{[^}]+\}", "1", path)
        response = anon.request(method, url, json={})
        if response.status_code != 401:
            unprotected.append((method, path, response.status_code))
    assert unprotected == []


@pytest.mark.parametrize("role", list(AgentRole))
def test_session_reports_the_permissions_of_the_role(db, role):
    make_agent(db, f"{role.value}@cm.test", role)
    client = login(f"{role.value}@cm.test")
    me = client.get("/api/auth/me").json()
    assert me["permissions"] == sorted(p.value for p in ROLE_PERMISSIONS[role])


def test_matrix():
    employee = ROLE_PERMISSIONS[AgentRole.AGENT]
    for permission in (
        Permission.CASES_MANAGE,
        Permission.CASES_HISTORY,
        Permission.TASKS_ASSIGN,
        Permission.PATIENTS_MANAGE,
        Permission.CONVERSATIONS_AREA,
        Permission.DIRECTORY_VIEW,
    ):
        assert permission in employee
    for permission in (
        Permission.METRICS_VIEW,
        Permission.USERS_MANAGE,
        Permission.CATALOG_MANAGE,
        Permission.CONVERSATIONS_ALL,
        Permission.SIMULATOR_USE,
        Permission.DIRECTORY_MANAGE,
    ):
        assert permission not in employee
    supervisor = ROLE_PERMISSIONS[AgentRole.SUPERVISOR]
    assert employee < supervisor
    assert Permission.METRICS_VIEW in supervisor
    assert Permission.USERS_MANAGE not in supervisor
    assert ROLE_PERMISSIONS[AgentRole.ADMIN] == frozenset(Permission)


def test_employee_creates_cases_assigns_work_and_reads_history(lab_agent, db):
    """Lo que pidió el centro: crear casos, asignar tareas a otros y ver la historia."""
    gaby_id = make_agent(db, "gaby@cm.test", area_slug="seguros-facturacion").id
    gaby = login("gaby@cm.test")

    patient = new_patient(lab_agent)
    case = new_case(lab_agent, db, patient["id"], slug="seguros-facturacion")
    cid = case["id"]
    assert new_task(lab_agent, cid, gaby_id, type="whatsapp").status_code == 201
    assert lab_agent.post(f"/api/cases/{cid}/assign", json={"agent_id": gaby_id}).status_code == 200
    assert (
        lab_agent.post(f"/api/cases/{cid}/notes", json={"body": "Llamar mañana"}).status_code == 201
    )
    assert to_stage(gaby, cid, "in_progress").status_code == 200

    # Cualquier empleado, de cualquier área, ve la historia completa.
    detail = gaby.get(f"/api/cases/{cid}").json()
    assert [e["type"] for e in detail["events"]] == [
        "created",
        "task_created",
        "assigned",
        "note_added",
        "stage_changed",
    ]
    assert detail["notes"][0]["body"] == "Llamar mañana"
    assert detail["tasks"][0]["assigned_agent"]["name"] == "Gaby"
    assert gaby.get(f"/api/patients/{patient['id']}").json()["cases"][0]["id"] == cid
    closed = gaby.post("/api/cases/search", json={"stage": "all"}).json()["items"]
    assert [c["id"] for c in closed] == [cid]


def test_employee_reads_the_chat_of_a_case_from_another_area(anon, lab_agent, db):
    patient_says(anon, "Hola")
    patient_says(anon, "2")  # Laboratorio
    conversation_id = lab_agent.get("/api/inbox", params={"filter": "queue"}).json()["items"][0][
        "id"
    ]
    case = new_case(lab_agent, db, new_patient(lab_agent)["id"], conversation_id=conversation_id)

    make_agent(db, "gaby@cm.test", area_slug="seguros-facturacion")
    gaby = login("gaby@cm.test")
    # El chat no es de su área: no lo ve en Conversaciones ni puede escribir en él…
    assert gaby.get(f"/api/conversations/{conversation_id}").status_code == 404
    note = {"body": "x", "is_internal_note": True}
    assert gaby.post(f"/api/conversations/{conversation_id}/messages", json=note).status_code == 404
    assert gaby.get(f"/api/cases/{case['id']}").json()["can_view_conversation"] is False
    # …pero sí lo lee como parte de la historia del caso.
    chat = gaby.get(f"/api/cases/{case['id']}/conversation").json()
    assert chat["id"] == conversation_id
    assert [m["body"] for m in chat["messages"] if m["sender_type"] == "contact"] == ["Hola", "2"]

    plain = new_case(lab_agent, db, new_patient(lab_agent, national_id="V7777777")["id"])
    assert gaby.get(f"/api/cases/{plain['id']}/conversation").status_code == 400


def test_employee_cannot_reach_management(lab_agent, db):
    params = {"from": "2026-11-01", "to": "2026-11-02"}
    assert lab_agent.get("/api/metrics/overview", params=params).status_code == 403
    assert lab_agent.get("/api/metrics/cases/overview", params=params).status_code == 403
    assert lab_agent.get("/api/admin/agents").status_code == 403
    assert lab_agent.get("/api/admin/areas").status_code == 403
    new_user = {"name": "Otro", "email": "otro@cm.test", "password": "clave-segura-123"}
    assert lab_agent.post("/api/admin/agents", json=new_user).status_code == 403
    assert lab_agent.post("/api/dev/simulate-inbound", json={"text": "hola"}).status_code == 403
    # Lo suyo sí: catálogo para trabajar y su propia contraseña.
    assert lab_agent.get("/api/catalog").status_code == 200
    assert area_id(db, "laboratorio")


def test_supervisor_sees_metrics_but_not_user_management(supervisor):
    params = {"from": "2026-11-01", "to": "2026-11-02"}
    assert supervisor.get("/api/metrics/overview", params=params).status_code == 200
    assert supervisor.get("/api/metrics/cases/overview", params=params).status_code == 200
    assert supervisor.get("/api/admin/agents").status_code == 403
    assert supervisor.get("/api/admin/areas").status_code == 403
    assert supervisor.post("/api/dev/simulate-inbound", json={"text": "hola"}).status_code != 403
