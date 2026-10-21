from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update

from app.db.base import utcnow
from app.models import Contact, Conversation, ConversationEvent, Message, Survey
from app.models.enums import ConversationStatus, EventType, SurveyKind, SurveyStatus
from app.services import surveys
from tests.conftest import patient_says, reason_id


def close_lab_case(anon, db, agent, wa_id="584141234567", send_survey=True):
    patient_says(anon, "Hola", wa_id)
    patient_says(anon, "2", wa_id)
    cid = db.scalar(select(func.max(Conversation.id)))
    agent.post(f"/api/conversations/{cid}/accept")
    response = agent.post(
        f"/api/conversations/{cid}/close",
        json={"contact_reason_id": reason_id(db), "send_survey": send_survey},
    )
    assert response.status_code == 200
    return cid, response.json()


def test_parse_score():
    assert surveys.parse_score("5", SurveyKind.CSAT) == 5
    assert surveys.parse_score(" 4/5 ", SurveyKind.CSAT) == 4
    assert surveys.parse_score("⭐⭐⭐", SurveyKind.CSAT) == 3
    assert surveys.parse_score("6", SurveyKind.CSAT) is None
    assert surveys.parse_score("0", SurveyKind.CSAT) is None
    assert surveys.parse_score("10", SurveyKind.NPS) == 10
    assert surveys.parse_score("0", SurveyKind.NPS) == 0
    assert surveys.parse_score("gracias, 5 estrellas", SurveyKind.CSAT) is None


def test_close_sends_csat_template_and_answer_is_captured(anon, db, lab_agent):
    cid, closed = close_lab_case(anon, db, lab_agent)
    assert [s["kind"] for s in closed["surveys"]] == ["csat"]
    template = db.scalar(select(Message).where(Message.message_type == "template"))
    assert template.status.value == "simulated"

    patient_says(anon, "5")
    survey = db.scalar(select(Survey))
    db.refresh(survey)
    assert survey.status == SurveyStatus.ANSWERED and survey.score == 5
    conversation = db.get(Conversation, cid)
    db.refresh(conversation)
    assert conversation.status == ConversationStatus.CLOSED  # la respuesta no reabre el caso
    answered = db.scalar(
        select(ConversationEvent).where(ConversationEvent.type == EventType.SURVEY_ANSWERED)
    )
    assert answered.data == {"survey_id": survey.id, "kind": "csat", "score": 5}
    assert db.scalar(select(func.count()).select_from(Conversation)) == 1


def test_other_message_expires_survey_and_reopens(anon, db, lab_agent):
    cid, _ = close_lab_case(anon, db, lab_agent)
    patient_says(anon, "Disculpe, me faltó preguntar algo")
    survey = db.scalar(select(Survey))
    db.refresh(survey)
    assert survey.status == SurveyStatus.EXPIRED
    conversation = db.get(Conversation, cid)
    db.refresh(conversation)
    assert conversation.status == ConversationStatus.QUEUED
    patient_says(anon, "5")  # ya no se toma como calificación
    db.refresh(survey)
    assert survey.score is None


def test_csat_respects_cooldown_and_opt_out_flag(anon, db, lab_agent):
    _, first = close_lab_case(anon, db, lab_agent)
    assert len(first["surveys"]) == 1
    patient_says(anon, "4")
    db.execute(update(Conversation).values(closed_at=utcnow() - timedelta(hours=72)))
    db.commit()

    _, second = close_lab_case(anon, db, lab_agent)  # dentro del enfriamiento de 30 días
    assert second["surveys"] == []
    _, third = close_lab_case(anon, db, lab_agent, wa_id="584149999999", send_survey=False)
    assert third["surveys"] == []


def test_no_csat_after_urgency(anon, db, general_agent):
    patient_says(anon, "mi papá tiene dolor de pecho")
    cid = db.scalar(select(Conversation.id))
    detail = general_agent.get(f"/api/conversations/{cid}").json()
    assert detail["csat_skip_reason"] == "urgent"
    general_agent.post(f"/api/conversations/{cid}/accept")
    closed = general_agent.post(
        f"/api/conversations/{cid}/close", json={"contact_reason_id": reason_id(db)}
    ).json()
    assert closed["surveys"] == []


def test_monthly_nps_samples_only_consenting_contacts_once(anon, db, lab_agent):
    close_lab_case(anon, db, lab_agent, wa_id="584140000011", send_survey=False)
    close_lab_case(anon, db, lab_agent, wa_id="584140000022", send_survey=False)
    db.execute(update(Contact).where(Contact.wa_id == "584140000011").values(opt_in_at=utcnow()))
    db.commit()

    first_of_month = datetime(2026, 11, 1, 14, 0, tzinfo=UTC)  # 10:00 en Caracas
    assert surveys.run_monthly_nps(db, first_of_month - timedelta(days=1)) == 0
    assert surveys.run_monthly_nps(db, first_of_month) == 1
    assert surveys.run_monthly_nps(db, first_of_month + timedelta(hours=2)) == 0
    nps = db.scalar(select(Survey).where(Survey.kind == SurveyKind.NPS))
    assert db.get(Contact, nps.contact_id).wa_id == "584140000011"


def test_consent_endpoint(anon, db, lab_agent, general_agent):
    close_lab_case(anon, db, lab_agent)
    contact_id = db.scalar(select(Contact.id))
    granted = lab_agent.put(f"/api/contacts/{contact_id}/consent", json={"opt_in": True})
    assert granted.status_code == 200 and granted.json()["opt_in_at"] is not None
    # Un agente que no ve ninguna conversación del contacto no puede cambiarlo.
    assert (
        general_agent.put(f"/api/contacts/{contact_id}/consent", json={"opt_in": False}).status_code
        == 404
    )
    revoked = lab_agent.put(f"/api/contacts/{contact_id}/consent", json={"opt_in": False})
    assert revoked.json()["opt_in_at"] is None
