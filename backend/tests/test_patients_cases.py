from datetime import timedelta

from sqlalchemy import select, update

from app.db.base import utcnow
from app.models import Case, CaseEvent, ConversationEvent, Patient
from app.models.enums import EventType
from tests.conftest import area_id, login, make_agent, patient_says, reason_id

PATIENT = {
    "first_name": "María",
    "last_name": "Pérez",
    "national_id": "V-12.345.678",
    "phone": "0414-1234567",
    "email": "maria@example.com",
}


def new_patient(client, **overrides) -> dict:
    response = client.post("/api/patients", json={**PATIENT, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def new_case(client, db, patient_id, slug="laboratorio", **overrides) -> dict:
    body = {
        "patient_id": patient_id,
        "area_id": area_id(db, slug),
        "subject": "Resultados retrasados",
        **overrides,
    }
    response = client.post("/api/cases", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def to_stage(client, case_id, stage, **extra):
    return client.post(f"/api/cases/{case_id}/stage", json={"stage": stage, **extra})


def test_patient_requires_all_fields_and_normalizes(lab_agent):
    for field in PATIENT:
        body = {k: v for k, v in PATIENT.items() if k != field}
        assert lab_agent.post("/api/patients", json=body).status_code == 422, field
    bad = lab_agent.post("/api/patients", json={**PATIENT, "email": "no-es-correo"})
    assert bad.status_code == 422

    patient = new_patient(lab_agent)
    assert patient["national_id"] == "V12345678"
    assert patient["phone"] == "584141234567"


def test_national_id_is_unique_however_it_is_written(lab_agent):
    new_patient(lab_agent)
    duplicate = lab_agent.post("/api/patients", json={**PATIENT, "national_id": "v12345678"})
    assert duplicate.status_code == 409


def test_patient_search_by_name_id_and_phone(lab_agent):
    patient = new_patient(lab_agent)
    new_patient(lab_agent, first_name="Ana", last_name="Gómez", national_id="V999999")
    for q in ["maría pérez", "12.345.678", "0414-1234567", "584141234567"]:
        items = lab_agent.post("/api/patients/search", json={"q": q}).json()["items"]
        assert patient["id"] in [i["id"] for i in items], q
    assert len(lab_agent.post("/api/patients/search", json={"q": "gómez"}).json()["items"]) == 1
    assert len(lab_agent.post("/api/patients/search", json={"q": "100%"}).json()["items"]) == 0


def test_case_lifecycle_with_events(lab_agent, db):
    patient = new_patient(lab_agent)
    case = new_case(lab_agent, db, patient["id"])
    assert case["stage"] == "registered"
    assert case["assigned_agent"] is None
    assert case["next_stages"] == ["in_progress"]
    cid = case["id"]

    started = to_stage(lab_agent, cid, "in_progress").json()
    assert started["assigned_agent"]["name"] == "Lab"  # quien lo atiende queda como responsable
    assert to_stage(lab_agent, cid, "waiting").json()["next_stages"] == ["in_progress"]
    assert to_stage(lab_agent, cid, "in_progress").status_code == 200
    resolved = to_stage(lab_agent, cid, "resolved").json()
    assert resolved["resolved_at"] is not None

    assert to_stage(lab_agent, cid, "closed").status_code == 400  # falta el motivo
    closed = to_stage(lab_agent, cid, "closed", contact_reason_id=reason_id(db)).json()
    assert closed["closed_at"] is not None
    assert closed["contact_reason"]["name"] == "Información general"

    reopened = to_stage(lab_agent, cid, "in_progress").json()
    assert reopened["closed_at"] is None
    assert reopened["resolved_at"] is None

    rows = list(db.scalars(select(CaseEvent).where(CaseEvent.case_id == cid)))
    assert [e.data.get("to") for e in rows] == [
        None,
        "in_progress",
        "waiting",
        "in_progress",
        "resolved",
        "closed",
        "in_progress",
    ]


def test_invalid_or_stale_stage_step_conflicts(lab_agent, db):
    case = new_case(lab_agent, db, new_patient(lab_agent)["id"])
    assert to_stage(lab_agent, case["id"], "closed").status_code == 409
    assert to_stage(lab_agent, case["id"], "in_progress").status_code == 200
    # Una segunda tableta con la pantalla vieja pulsa lo mismo.
    assert to_stage(lab_agent, case["id"], "in_progress").status_code == 409


def test_any_area_sees_and_manages_any_case(lab_agent, db):
    make_agent(db, "seguros@cm.test", area_slug="seguros-facturacion")
    other = login("seguros@cm.test")
    case = new_case(lab_agent, db, new_patient(lab_agent)["id"])
    assert other.get(f"/api/cases/{case['id']}").status_code == 200
    assert other.post("/api/cases/search", json={}).json()["items"][0]["id"] == case["id"]
    assert to_stage(other, case["id"], "in_progress").status_code == 200


def test_transfer_returns_to_registered_in_the_new_area(lab_agent, db):
    case = new_case(lab_agent, db, new_patient(lab_agent)["id"])
    to_stage(lab_agent, case["id"], "in_progress")
    target = area_id(db, "seguros-facturacion")
    moved = lab_agent.post(f"/api/cases/{case['id']}/transfer", json={"area_id": target}).json()
    assert moved["stage"] == "registered"
    assert moved["area"]["id"] == target
    assert moved["assigned_agent"] is None
    same = lab_agent.post(f"/api/cases/{case['id']}/transfer", json={"area_id": target})
    assert same.status_code == 400

    to_stage(lab_agent, case["id"], "in_progress")
    to_stage(lab_agent, case["id"], "resolved")
    late = lab_agent.post(
        f"/api/cases/{case['id']}/transfer", json={"area_id": area_id(db, "laboratorio")}
    )
    assert late.status_code == 409


def test_search_filters(lab_agent, db):
    patient = new_patient(lab_agent)
    first = new_case(lab_agent, db, patient["id"], subject="Primero")
    urgent = new_case(lab_agent, db, patient["id"], subject="Segundo", priority="high")
    closed = new_case(lab_agent, db, patient["id"], subject="Tercero")
    to_stage(lab_agent, closed["id"], "in_progress")
    to_stage(lab_agent, closed["id"], "resolved")
    to_stage(lab_agent, closed["id"], "closed", contact_reason_id=reason_id(db))

    def ids(**body):
        return [c["id"] for c in lab_agent.post("/api/cases/search", json=body).json()["items"]]

    assert ids() == [urgent["id"], first["id"]]  # urgentes primero y sin los cerrados
    assert ids(stage="closed") == [closed["id"]]
    assert ids(q="tercero") == []
    assert ids(q="tercero", stage="all") == [closed["id"]]
    assert set(ids(q="V12345678")) == {first["id"], urgent["id"]}
    assert ids(q=f"#{first['id']}") == [first["id"]]
    assert ids(mine=True) == []
    assert ids(area_id=area_id(db, "seguros-facturacion")) == []


def test_case_from_conversation_links_contact(anon, lab_agent, db):
    patient_says(anon, "Hola")
    patient_says(anon, "2")  # Laboratorio
    cid = lab_agent.get("/api/inbox", params={"filter": "queue"}).json()["items"][0]["id"]
    before = lab_agent.get(f"/api/conversations/{cid}").json()
    assert before["patient"] is None and before["cases"] == []

    patient = new_patient(lab_agent)
    case = new_case(lab_agent, db, patient["id"], conversation_id=cid)
    assert case["conversation_id"] == cid
    assert case["can_view_conversation"] is True

    after = lab_agent.get(f"/api/conversations/{cid}").json()
    assert after["patient"]["id"] == patient["id"]
    assert [c["id"] for c in after["cases"]] == [case["id"]]
    assert EventType.CASE_CREATED in [
        e.type
        for e in db.scalars(
            select(ConversationEvent).where(ConversationEvent.conversation_id == cid)
        )
    ]

    # Una madre escribe por otro hijo: el número no se reasigna.
    second = new_patient(lab_agent, national_id="V777777")
    new_case(lab_agent, db, second["id"], conversation_id=cid)
    assert db.get(Patient, second["id"]).contact_id is None


def test_case_from_invisible_conversation_is_rejected(anon, lab_agent, db):
    patient_says(anon, "Hola")
    patient_says(anon, "2")
    cid = lab_agent.get("/api/inbox", params={"filter": "queue"}).json()["items"][0]["id"]
    make_agent(db, "seguros@cm.test", area_slug="seguros-facturacion")
    other = login("seguros@cm.test")
    patient = new_patient(other)
    body = {
        "patient_id": patient["id"],
        "area_id": area_id(db, "laboratorio"),
        "subject": "Otro",
        "conversation_id": cid,
    }
    assert other.post("/api/cases", json=body).status_code == 404


def test_events_never_contain_patient_text(lab_agent, db):
    secret = "Tiene diabetes"
    case = new_case(lab_agent, db, new_patient(lab_agent)["id"], description=secret)
    lab_agent.post(f"/api/cases/{case['id']}/notes", json={"body": secret})
    lab_agent.patch(f"/api/cases/{case['id']}", json={"subject": f"{secret} tipo 2"})
    detail = lab_agent.get(f"/api/cases/{case['id']}").json()
    assert detail["notes"][0]["body"] == secret
    for event in db.scalars(select(CaseEvent).where(CaseEvent.case_id == case["id"])):
        assert "diabetes" not in str(event.data)


def test_live_board(lab_agent, db):
    patient = new_patient(lab_agent)
    late = new_case(lab_agent, db, patient["id"], priority="high")
    fresh = new_case(lab_agent, db, patient["id"])
    working = new_case(lab_agent, db, patient["id"], slug="seguros-facturacion")
    to_stage(lab_agent, working["id"], "in_progress")
    finished = new_case(lab_agent, db, patient["id"])
    to_stage(lab_agent, finished["id"], "in_progress")
    to_stage(lab_agent, finished["id"], "resolved")
    to_stage(lab_agent, finished["id"], "closed", contact_reason_id=reason_id(db))

    # Laboratorio tiene meta de 15 min: este caso lleva 20 sin atender.
    old = utcnow() - timedelta(minutes=20)
    db.execute(update(Case).where(Case.id == late["id"]).values(stage_changed_at=old))
    db.commit()

    live = lab_agent.get("/api/cases/live").json()
    assert live["registered"] == 2
    assert live["in_progress"] == 1
    assert live["late"] == 1
    assert live["urgent"] == 1
    assert live["created_today"] == 4
    assert live["closed_today"] == 1
    assert live["first_attention_median"] is not None
    assert live["resolution_median"] is not None
    by_area = {a["area"]["name"]: a for a in live["areas"]}
    assert by_area["Laboratorio"]["registered"] == 2
    assert by_area["Laboratorio"]["late"] == 1
    assert by_area["Seguros y facturación"]["in_progress"] == 1
    assert by_area["Hospitalización"]["registered"] == 0
    assert fresh["id"]


def test_waiting_time_is_discounted_from_resolution(lab_agent, db):
    case = new_case(lab_agent, db, new_patient(lab_agent)["id"])
    cid = case["id"]
    to_stage(lab_agent, cid, "in_progress")
    to_stage(lab_agent, cid, "waiting")
    to_stage(lab_agent, cid, "in_progress")
    to_stage(lab_agent, cid, "resolved")

    start = utcnow() - timedelta(minutes=60)
    rows = list(
        db.scalars(select(CaseEvent).where(CaseEvent.case_id == cid).order_by(CaseEvent.id))
    )
    offsets = [0, 10, 20, 50, 60]  # 30 min en espera, de 60 en total
    for event, minutes in zip(rows, offsets, strict=True):
        event.created_at = start + timedelta(minutes=minutes)
    row = db.get(Case, cid)
    row.opened_at = start
    row.resolved_at = start + timedelta(minutes=60)
    db.commit()

    live = lab_agent.get("/api/cases/live").json()
    assert live["resolution_median"] == 30.0
    assert live["first_attention_median"] == 10.0


def test_every_change_is_recorded_under_who_made_it(lab_agent, db):
    """Cada persona con su cuenta: el historial dice quién hizo cada cosa."""
    make_agent(db, "luis@cm.test", area_slug="seguros-facturacion")
    luis = login("luis@cm.test")

    patient = new_patient(lab_agent)
    edited = luis.patch(f"/api/patients/{patient['id']}", json={"email": "otro@example.com"})
    assert edited.status_code == 200
    # Guardar sin cambios no deja rastro falso.
    luis.patch(f"/api/patients/{patient['id']}", json={"email": "otro@example.com"})
    history = lab_agent.get(f"/api/patients/{patient['id']}").json()["events"]
    assert [(e["type"], e["agent"]["name"]) for e in history] == [
        ("created", "Lab"),
        ("updated", "Luis"),
    ]
    assert history[1]["data"] == {"fields": ["email"]}  # el nombre del campo, nunca su valor

    case = new_case(lab_agent, db, patient["id"])
    cid = case["id"]
    to_stage(luis, cid, "in_progress")
    lab_agent.post(f"/api/cases/{cid}/take")
    luis.post(f"/api/cases/{cid}/notes", json={"body": "Nota"})
    lab_agent.patch(f"/api/cases/{cid}", json={"subject": "Asunto nuevo"})
    luis.post(f"/api/cases/{cid}/transfer", json={"area_id": area_id(db, "imagenologia")})
    detail = lab_agent.get(f"/api/cases/{cid}").json()
    assert [(e["type"], e["agent"]["name"]) for e in detail["events"]] == [
        ("created", "Lab"),
        ("stage_changed", "Luis"),
        ("taken", "Lab"),
        ("note_added", "Luis"),
        ("updated", "Lab"),
        ("transferred", "Luis"),
    ]
    assert detail["notes"][0]["agent"]["name"] == "Luis"


def test_contact_link_is_recorded(anon, lab_agent, db):
    patient_says(anon, "Hola")
    patient_says(anon, "2")
    cid = lab_agent.get("/api/inbox", params={"filter": "queue"}).json()["items"][0]["id"]
    patient = new_patient(lab_agent)
    new_case(lab_agent, db, patient["id"], conversation_id=cid)
    history = lab_agent.get(f"/api/patients/{patient['id']}").json()["events"]
    assert history[-1]["type"] == "contact_linked" and history[-1]["agent"]["name"] == "Lab"


def test_goal_is_the_same_for_all_areas(lab_agent, db):
    patient = new_patient(lab_agent)
    # Atención al paciente tiene meta de WhatsApp de 10 min; la de casos es 15 en todas.
    case = new_case(lab_agent, db, patient["id"], slug="atencion-paciente")
    db.execute(
        update(Case)
        .where(Case.id == case["id"])
        .values(stage_changed_at=utcnow() - timedelta(minutes=12))
    )
    db.commit()
    live = lab_agent.get("/api/cases/live").json()
    assert live["goal_minutes"] == 15
    assert live["late"] == 0
    page = lab_agent.post("/api/cases/search", json={}).json()
    assert page["goal_minutes"] == 15
