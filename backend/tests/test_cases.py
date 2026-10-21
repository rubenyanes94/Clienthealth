from datetime import timedelta

from sqlalchemy import select, update

from app.db.base import utcnow
from app.models import Conversation, ConversationEvent, Message
from app.models.enums import ConversationStatus, EventType
from tests.conftest import area_id, login, make_agent, patient_says, reason_id


def queue_lab_case(anon, wa_id="584141234567"):
    patient_says(anon, "Hola", wa_id)
    patient_says(anon, "2", wa_id)  # Laboratorio


def event_types(db, conversation_id):
    return [
        e.type
        for e in db.scalars(
            select(ConversationEvent)
            .where(ConversationEvent.conversation_id == conversation_id)
            .order_by(ConversationEvent.id)
        )
    ]


def test_full_case_lifecycle(anon, db, lab_agent):
    """Criterio de la fase 1: entra por el webhook, se acepta, se responde y se cierra."""
    queue_lab_case(anon)
    queue = lab_agent.get("/api/inbox", params={"filter": "queue"}).json()["items"]
    assert len(queue) == 1
    cid = queue[0]["id"]
    assert queue[0]["contact"]["name"] == "María Pérez"
    assert queue[0]["last_message_preview"].startswith("Le estamos comunicando")

    assert lab_agent.post(f"/api/conversations/{cid}/accept").json()["status"] == "open"

    reply = lab_agent.post(
        f"/api/conversations/{cid}/messages", json={"body": "Buenos días, ¿en qué le ayudo?"}
    )
    assert reply.status_code == 201
    assert reply.json()["status"] == "simulated"

    note = lab_agent.post(
        f"/api/conversations/{cid}/messages",
        json={"body": "Paciente frecuente", "is_internal_note": True},
    )
    assert note.json()["is_internal_note"] is True

    assert lab_agent.post(f"/api/conversations/{cid}/pending").json()["status"] == "pending"
    patient_says(anon, "Ya le envío la orden")  # reanuda automáticamente
    detail = lab_agent.get(f"/api/conversations/{cid}").json()
    assert detail["status"] == "open"
    assert detail["pending_since"] is None

    no_reason = lab_agent.post(f"/api/conversations/{cid}/close", json={})
    assert no_reason.status_code == 422
    closed = lab_agent.post(
        f"/api/conversations/{cid}/close",
        json={"contact_reason_id": reason_id(db, "Resultados de laboratorio")},
    )
    assert closed.json()["status"] == "closed"
    assert closed.json()["contact_reason"]["name"] == "Resultados de laboratorio"

    assert event_types(db, cid) == [
        EventType.CREATED,
        EventType.INBOUND_MESSAGE,
        EventType.BOT_MESSAGE,
        EventType.INBOUND_MESSAGE,
        EventType.BOT_ESCALATED,
        EventType.BOT_MESSAGE,
        EventType.ACCEPTED,
        EventType.AGENT_MESSAGE,
        EventType.INTERNAL_NOTE,
        EventType.PENDING_STARTED,
        EventType.INBOUND_MESSAGE,
        EventType.PENDING_RESUMED,
        EventType.CLOSED,
    ]
    # Ningún evento guarda texto del paciente ni del agente.
    texts = [m.body for m in db.scalars(select(Message)) if len(m.body) > 3]
    for event in db.scalars(select(ConversationEvent)):
        serialized = str(event.data)
        assert not any(t in serialized for t in texts)


def test_agent_of_other_area_cannot_see_or_accept(anon, db, general_agent):
    queue_lab_case(anon)
    cid = db.scalar(select(Conversation.id))
    assert general_agent.get("/api/inbox", params={"filter": "queue"}).json()["items"] == []
    assert general_agent.get(f"/api/conversations/{cid}").status_code == 404
    assert general_agent.post(f"/api/conversations/{cid}/accept").status_code == 404


def test_second_agent_cannot_take_accepted_case(anon, db, lab_agent):
    make_agent(db, "lab2@example.com", area_slug="laboratorio")
    other = login("lab2@example.com")
    queue_lab_case(anon)
    cid = db.scalar(select(Conversation.id))

    # El segundo agente ve el cambio en el polling aunque el caso ya no sea suyo.
    since = other.get("/api/inbox/changes", params={"since": utcnow().isoformat()}).json()
    assert lab_agent.post(f"/api/conversations/{cid}/accept").status_code == 200
    assert other.post(f"/api/conversations/{cid}/accept").status_code == 404
    changes = other.get("/api/inbox/changes", params={"since": since["server_time"]}).json()
    assert changes["ids"] == [cid]
    assert (
        other.post(f"/api/conversations/{cid}/messages", json={"body": "hola"}).status_code == 404
    )


def test_reply_requires_accept_and_open_window(anon, db, lab_agent):
    queue_lab_case(anon)
    cid = db.scalar(select(Conversation.id))
    early = lab_agent.post(f"/api/conversations/{cid}/messages", json={"body": "hola"})
    assert early.status_code == 409

    lab_agent.post(f"/api/conversations/{cid}/accept")
    db.execute(update(Conversation).values(last_inbound_at=utcnow() - timedelta(hours=25)))
    db.commit()
    late = lab_agent.post(f"/api/conversations/{cid}/messages", json={"body": "hola"})
    assert late.status_code == 409
    assert "24 h" in late.json()["detail"]


def test_transfer_sends_case_to_other_area_queue(anon, db, lab_agent, general_agent):
    queue_lab_case(anon)
    cid = db.scalar(select(Conversation.id))
    lab_agent.post(f"/api/conversations/{cid}/accept")
    response = lab_agent.post(
        f"/api/conversations/{cid}/transfer",
        json={"area_id": area_id(db, "atencion-paciente")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert response.json()["assigned_agent"] is None

    queue = general_agent.get("/api/inbox", params={"filter": "queue"}).json()["items"]
    assert [c["id"] for c in queue] == [cid]
    event = db.scalar(
        select(ConversationEvent).where(ConversationEvent.type == EventType.TRANSFERRED)
    )
    assert event.data == {
        "from_area_id": area_id(db, "laboratorio"),
        "to_area_id": area_id(db, "atencion-paciente"),
    }


def test_patient_writing_back_reopens_within_window(anon, db, lab_agent):
    queue_lab_case(anon)
    cid = db.scalar(select(Conversation.id))
    lab_agent.post(f"/api/conversations/{cid}/accept")
    lab_agent.post(f"/api/conversations/{cid}/close", json={"contact_reason_id": reason_id(db)})

    patient_says(anon, "Disculpe, otra pregunta")
    conversation = db.get(Conversation, cid)
    db.refresh(conversation)
    assert conversation.status == ConversationStatus.QUEUED
    assert conversation.closed_at is None
    reopened = db.scalar(
        select(ConversationEvent).where(ConversationEvent.type == EventType.REOPENED)
    )
    assert reopened.data["by"] == "contact"


def test_patient_writing_after_window_opens_new_conversation(anon, db, lab_agent):
    queue_lab_case(anon)
    cid = db.scalar(select(Conversation.id))
    lab_agent.post(f"/api/conversations/{cid}/accept")
    lab_agent.post(f"/api/conversations/{cid}/close", json={"contact_reason_id": reason_id(db)})
    db.execute(update(Conversation).values(closed_at=utcnow() - timedelta(hours=72)))
    db.commit()

    patient_says(anon, "Hola de nuevo")
    rows = db.scalars(select(Conversation).order_by(Conversation.id)).all()
    assert len(rows) == 2
    assert rows[1].status == ConversationStatus.BOT


def test_agent_reopens_own_closed_case(anon, db, lab_agent):
    queue_lab_case(anon)
    cid = db.scalar(select(Conversation.id))
    lab_agent.post(f"/api/conversations/{cid}/accept")
    lab_agent.post(f"/api/conversations/{cid}/close", json={"contact_reason_id": reason_id(db)})
    response = lab_agent.post(f"/api/conversations/{cid}/reopen")
    assert response.status_code == 200
    assert response.json()["status"] == "open"


def test_supervisor_sees_bot_conversations_and_can_intervene(anon, db, supervisor, lab_agent):
    patient_says(anon, "Hola")
    cid = db.scalar(select(Conversation.id))
    assert lab_agent.get("/api/inbox", params={"filter": "open"}).json()["items"] == []
    items = supervisor.get("/api/inbox", params={"filter": "bot"}).json()["items"]
    assert [c["id"] for c in items] == [cid]
    assert lab_agent.post(f"/api/conversations/{cid}/accept").status_code == 404
    taken = supervisor.post(f"/api/conversations/{cid}/accept")
    assert taken.status_code == 200
    assert taken.json()["status"] == "open"
