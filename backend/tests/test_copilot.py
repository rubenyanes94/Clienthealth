import json

import pytest
from sqlalchemy import select

from app.models import Contact, Conversation
from app.services import copilot
from tests.conftest import patient_says, reason_id


@pytest.fixture
def fake_gemini(monkeypatch):
    calls: list[dict] = []

    def fake(prompt, schema=None):
        calls.append({"prompt": prompt, "schema": schema})
        if schema:
            return json.dumps({"reason_id": calls[0].get("reason_id")})
        return "Buenas tardes, [PACIENTE]. Con gusto le ayudo."

    monkeypatch.setattr(copilot, "_generate", fake)
    return calls


def lab_case(anon, db, agent):
    patient_says(anon, "Hola")
    patient_says(anon, "2")
    patient_says(anon, "Soy María Pérez, C.I. V-12.345.678, mi otro número es 0414-555.12.34")
    cid = db.scalar(select(Conversation.id))
    agent.post(f"/api/conversations/{cid}/accept")
    return cid


def test_pseudonymize_removes_identifiers():
    contact = Contact(wa_id="584141234567", name="María José Pérez")
    text = "Soy Maria Perez, V-12.345.678, 0414-123.45.67, mj@gmail.com. Gracias María."
    clean = copilot.pseudonymize(text, contact)
    assert clean == ("Soy [PACIENTE] [PACIENTE], [CÉDULA], [NÚMERO], [CORREO]. Gracias [PACIENTE].")


def test_prompt_never_contains_patient_identifiers(anon, db, lab_agent, fake_gemini):
    cid = lab_case(anon, db, lab_agent)
    lab_agent.post(
        f"/api/conversations/{cid}/messages",
        json={"body": "Nota: paciente María, tel 04145551234", "is_internal_note": True},
    )
    response = lab_agent.post(f"/api/copilot/{cid}/suggest")
    assert response.status_code == 200
    # El nombre vuelve a la propuesta solo en el servidor, para el agente.
    assert response.json()["text"] == "Buenas tardes, María. Con gusto le ayudo."

    prompt = fake_gemini[0]["prompt"]
    for leaked in ("María", "Maria", "Pérez", "12.345.678", "0414", "584141234567"):
        assert leaked not in prompt
    assert "[PACIENTE]" in prompt
    assert "Nota:" not in prompt  # las notas internas no salen


def test_summary_and_rewrite(anon, db, lab_agent, fake_gemini):
    cid = lab_case(anon, db, lab_agent)
    assert lab_agent.post(f"/api/copilot/{cid}/summary").status_code == 200
    rewritten = lab_agent.post(
        f"/api/copilot/{cid}/rewrite", json={"draft": "maria ya le mando eso"}
    )
    assert rewritten.status_code == 200
    assert "maria" not in fake_gemini[-1]["prompt"].split("Borrador:")[1]


def test_suggest_reason_validates_against_catalog(anon, db, lab_agent, monkeypatch):
    cid = lab_case(anon, db, lab_agent)
    wanted = reason_id(db, "Resultados de laboratorio")
    monkeypatch.setattr(copilot, "_generate", lambda p, s=None: json.dumps({"reason_id": wanted}))
    assert lab_agent.post(f"/api/copilot/{cid}/reason").json()["reason"]["id"] == wanted

    monkeypatch.setattr(copilot, "_generate", lambda p, s=None: json.dumps({"reason_id": 99999}))
    assert lab_agent.post(f"/api/copilot/{cid}/reason").json() == {"reason": None}


def test_copilot_errors_are_clear(anon, db, lab_agent, general_agent):
    cid = lab_case(anon, db, lab_agent)
    unconfigured = lab_agent.post(f"/api/copilot/{cid}/summary")
    assert unconfigured.status_code == 503
    assert "GEMINI_API_KEY" in unconfigured.json()["detail"]
    # Sin acceso a la conversación tampoco hay copiloto.
    assert general_agent.post(f"/api/copilot/{cid}/summary").status_code == 404
