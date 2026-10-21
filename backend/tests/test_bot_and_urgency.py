from sqlalchemy import select

from app.models import Conversation, ConversationEvent, Message
from app.models.enums import ConversationStatus, EventType, Priority, SenderType
from app.services.urgency import is_urgent
from tests.conftest import area_id, patient_says


def events_of(db, conversation_id):
    return [
        e.type
        for e in db.scalars(
            select(ConversationEvent)
            .where(ConversationEvent.conversation_id == conversation_id)
            .order_by(ConversationEvent.id)
        )
    ]


def test_urgency_classifier_rules():
    assert is_urgent("Mi papá tiene DOLOR DE PECHO desde hace rato")
    assert is_urgent("mi hija está convulsionando!!")
    assert is_urgent("se desmayó en la casa")
    assert is_urgent("no puede respirar bien")
    assert not is_urgent("Buenos días, quería saber el precio de una resonancia")
    assert not is_urgent("necesito mis resultados de laboratorio")
    assert not is_urgent("")


def test_menu_choice_escalates_to_area(anon, db):
    patient_says(anon, "Hola")
    patient_says(anon, "2")  # Laboratorio
    conversation = db.scalar(select(Conversation))
    assert conversation.status == ConversationStatus.QUEUED
    assert conversation.area_id == area_id(db, "laboratorio")
    assert conversation.queued_at is not None
    assert EventType.BOT_ESCALATED in events_of(db, conversation.id)


def test_asking_for_a_human_escalates_to_default_area(anon, db):
    patient_says(anon, "Hola")
    patient_says(anon, "quiero hablar con un agente por favor")
    conversation = db.scalar(select(Conversation))
    assert conversation.status == ConversationStatus.QUEUED
    assert conversation.area_id == area_id(db, "atencion-paciente")


def test_invalid_answers_escalate_after_max_attempts(anon, db):
    patient_says(anon, "Hola")
    patient_says(anon, "mmm")
    patient_says(anon, "no sé")
    conversation = db.scalar(select(Conversation))
    assert conversation.status == ConversationStatus.BOT
    patient_says(anon, "???")
    db.refresh(conversation)
    assert conversation.status == ConversationStatus.QUEUED


def test_faq_flow_resolved_by_bot(anon, db):
    patient_says(anon, "Hola")
    patient_says(anon, "6")  # Preguntas frecuentes
    patient_says(anon, "1")  # Horario
    patient_says(anon, "1")  # Sí, era todo
    conversation = db.scalar(select(Conversation))
    assert conversation.status == ConversationStatus.CLOSED
    assert conversation.area_id is None
    kinds = events_of(db, conversation.id)
    assert EventType.BOT_RESOLVED in kinds
    assert kinds[-1] == EventType.CLOSED


def test_urgency_stops_bot_and_goes_first_in_queue(anon, db, general_agent):
    patient_says(anon, "Hola", wa_id="584140000001")
    patient_says(anon, "1", wa_id="584140000001")  # caso normal en cola
    patient_says(anon, "Ayuda, mi mamá tiene dolor de pecho", wa_id="584140000002")

    rows = db.scalars(select(Conversation).order_by(Conversation.id)).all()
    normal, urgent = rows
    assert urgent.is_urgent and urgent.priority == Priority.HIGH
    assert urgent.status == ConversationStatus.QUEUED
    assert urgent.bot_state is None
    kinds = events_of(db, urgent.id)
    assert EventType.URGENCY_DETECTED in kinds
    replies = db.scalars(
        select(Message).where(Message.conversation_id == urgent.id, Message.direction == "outbound")
    ).all()
    assert [m.sender_type for m in replies] == [SenderType.SYSTEM]  # solo el mensaje de Emergencia

    queue = general_agent.get("/api/inbox", params={"filter": "queue"}).json()["items"]
    assert [c["id"] for c in queue] == [urgent.id, normal.id]


def test_urgency_in_queued_conversation_is_flagged_once(anon, db):
    patient_says(anon, "Hola")
    patient_says(anon, "3")
    patient_says(anon, "se desmayó")
    patient_says(anon, "sigue desmayado")
    conversation = db.scalar(select(Conversation))
    assert conversation.is_urgent
    assert events_of(db, conversation.id).count(EventType.URGENCY_DETECTED) == 1
