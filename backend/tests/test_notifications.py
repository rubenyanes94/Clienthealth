from sqlalchemy import select

from app.models import CaseEvent
from tests.conftest import area_id, login, make_agent
from tests.test_patients_cases import new_case, new_patient, new_task, to_stage


def inbox(client) -> dict:
    return client.get("/api/notifications").json()


def assign(client, case_id, agent_id):
    return client.post(f"/api/cases/{case_id}/assign", json={"agent_id": agent_id})


def setup(lab_agent, db):
    luis_id = make_agent(db, "luis@cm.test", area_slug="seguros-facturacion").id
    luis = login("luis@cm.test")
    case = new_case(lab_agent, db, new_patient(lab_agent)["id"])
    return luis, luis_id, case["id"]


def test_assigned_task_notifies_only_the_assignee(lab_agent, db):
    luis, luis_id, cid = setup(lab_agent, db)
    assert new_task(lab_agent, cid, luis_id, type="whatsapp").status_code == 201

    data = inbox(luis)
    assert data["unread"] == 1
    item = data["items"][0]
    assert item["type"] == "task_assigned"
    assert item["task_type"] == "whatsapp"
    assert item["actor"]["name"] == "Lab"
    assert item["case"] == {
        "id": cid,
        "subject": "Resultados retrasados",
        "patient_name": "María Pérez",
    }
    assert item["read_at"] is None
    assert inbox(lab_agent) == {"unread": 0, "items": []}


def test_assigning_a_task_or_case_to_yourself_does_not_notify(lab_agent, db):
    _, _, cid = setup(lab_agent, db)
    me = lab_agent.get("/api/auth/me").json()["id"]
    new_task(lab_agent, cid, me)
    assert assign(lab_agent, cid, me).status_code == 200
    assert inbox(lab_agent)["unread"] == 0


def test_assigned_case_notifies_and_is_recorded(lab_agent, db):
    luis, luis_id, cid = setup(lab_agent, db)
    detail = assign(lab_agent, cid, luis_id).json()
    assert detail["assigned_agent"]["name"] == "Luis"
    assert [(e["type"], e["agent"]["name"]) for e in detail["events"]][-1] == ("assigned", "Lab")
    item = inbox(luis)["items"][0]
    assert item["type"] == "case_assigned" and item["task_type"] is None
    # Asignar otra vez a la misma persona no duplica el aviso ni el evento.
    assign(lab_agent, cid, luis_id)
    assert inbox(luis)["unread"] == 1


def test_assign_rejects_closed_case_and_inactive_user(lab_agent, db):
    luis, luis_id, cid = setup(lab_agent, db)
    gone = make_agent(db, "baja@cm.test")
    gone.is_active = False
    db.commit()
    assert assign(lab_agent, cid, gone.id).status_code == 400
    to_stage(lab_agent, cid, "in_progress")
    to_stage(lab_agent, cid, "resolved")
    to_stage(lab_agent, cid, "closed", contact_reason_id=1)
    assert assign(lab_agent, cid, luis_id).status_code == 409
    assert assign(lab_agent, 9999, luis_id).status_code == 404


def test_mark_read_and_read_all(lab_agent, db):
    luis, luis_id, cid = setup(lab_agent, db)
    new_task(lab_agent, cid, luis_id)
    new_task(lab_agent, cid, luis_id, type="email")
    assign(lab_agent, cid, luis_id)
    items = inbox(luis)["items"]
    assert inbox(luis)["unread"] == 3
    assert [i["type"] for i in items] == ["case_assigned", "task_assigned", "task_assigned"]

    assert luis.post(f"/api/notifications/{items[0]['id']}/read").status_code == 204
    assert luis.post(f"/api/notifications/{items[0]['id']}/read").status_code == 204  # idempotente
    assert inbox(luis)["unread"] == 2
    assert luis.post("/api/notifications/read-all").status_code == 204
    after = inbox(luis)
    assert after["unread"] == 0 and all(i["read_at"] for i in after["items"])


def test_notifications_are_private(lab_agent, db):
    luis, luis_id, cid = setup(lab_agent, db)
    new_task(lab_agent, cid, luis_id)
    nid = inbox(luis)["items"][0]["id"]
    assert lab_agent.post(f"/api/notifications/{nid}/read").status_code == 404
    assert inbox(luis)["unread"] == 1
    lab_agent.post("/api/notifications/read-all")  # solo toca las suyas
    assert inbox(luis)["unread"] == 1


def test_notifications_require_login(anon):
    assert anon.get("/api/notifications").status_code == 401


def test_the_list_is_capped_and_newest_first(lab_agent, db):
    luis, luis_id, cid = setup(lab_agent, db)
    for _ in range(32):
        new_task(lab_agent, cid, luis_id)
    data = inbox(luis)
    assert data["unread"] == 32 and len(data["items"]) == 30
    ids = [i["id"] for i in data["items"]]
    assert ids == sorted(ids, reverse=True)


def test_events_do_not_carry_patient_text(lab_agent, db):
    luis, luis_id, cid = setup(lab_agent, db)
    new_task(lab_agent, cid, luis_id, notes="Tiene diabetes")
    assign(lab_agent, cid, luis_id)
    for event in db.scalars(select(CaseEvent).where(CaseEvent.case_id == cid)):
        assert "diabetes" not in str(event.data)
    assert area_id(db, "laboratorio")  # el catálogo sigue disponible
