from sqlalchemy import func, select

from app.models import Conversation, Message
from app.models.enums import ConversationStatus, MessageStatus
from tests.conftest import load_fixture, post_webhook, sign, status_payload, text_payload


def test_health(anon):
    response = anon.get("/api/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.json()["whatsapp_dry_run"] is True


def test_verification_handshake(anon):
    ok = anon.get(
        "/api/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "1158201444",
        },
    )
    assert ok.status_code == 200
    assert ok.text == "1158201444"

    bad = anon.get(
        "/api/webhooks/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "x"},
    )
    assert bad.status_code == 403


def test_rejects_invalid_signature(anon, db):
    raw = b'{"entry": []}'
    response = anon.post(
        "/api/webhooks/whatsapp", content=raw, headers={"X-Hub-Signature-256": "sha256=deadbeef"}
    )
    assert response.status_code == 401
    missing = anon.post("/api/webhooks/whatsapp", content=raw)
    assert missing.status_code == 401
    assert sign(raw).startswith("sha256=")


def test_real_meta_payload_creates_conversation_and_bot_replies(anon, db):
    assert post_webhook(anon, load_fixture("text_message.json")).status_code == 200

    conversation = db.scalar(select(Conversation))
    assert conversation.status == ConversationStatus.BOT
    assert conversation.contact.name == "María Pérez"
    messages = db.scalars(select(Message).order_by(Message.id)).all()
    assert [m.direction.value for m in messages] == ["inbound", "outbound"]
    assert messages[1].status == MessageStatus.SIMULATED
    assert "1. Atención al paciente" in messages[1].body


def test_duplicate_delivery_is_ignored(anon, db):
    payload = text_payload("Hola", wamid="wamid.duplicado")
    assert post_webhook(anon, payload).status_code == 200
    assert post_webhook(anon, payload).status_code == 200
    inbound = db.scalar(
        select(func.count()).select_from(Message).where(Message.external_id == "wamid.duplicado")
    )
    assert inbound == 1
    assert db.scalar(select(func.count()).select_from(Message)) == 2  # entrada + menú


def test_delivery_statuses_only_move_forward(anon, db):
    post_webhook(anon, text_payload("Hola"))
    outbound = db.scalar(select(Message).where(Message.direction == "outbound"))

    post_webhook(anon, status_payload(outbound.external_id, "read"))
    post_webhook(anon, status_payload(outbound.external_id, "delivered"))
    db.refresh(outbound)
    assert outbound.status == MessageStatus.READ

    post_webhook(anon, status_payload(outbound.external_id, "failed"))
    db.refresh(outbound)
    assert outbound.status == MessageStatus.FAILED


def test_media_message_is_stored_with_label(anon, db):
    payload = text_payload("x")
    message = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    message["type"] = "image"
    message.pop("text")
    message["image"] = {"id": "1234", "mime_type": "image/jpeg"}
    assert post_webhook(anon, payload).status_code == 200
    inbound = db.scalar(select(Message).where(Message.direction == "inbound"))
    assert inbound.message_type == "image"
    assert inbound.body == "[imagen]"
