"""El script de demostración deja datos coherentes y solo borra lo suyo."""

import sys

from sqlalchemy import func, select

from app.models import (
    Case,
    CaseEvent,
    CaseTask,
    Contact,
    Notification,
    Patient,
)
from app.models.enums import (
    AgentRole,
    CaseEventType,
    CaseStage,
    CaseTaskStatus,
)
from scripts import demo_data
from tests.conftest import make_agent


def run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["demo_data", *args])
    demo_data.main()


def test_demo_data_is_coherent_and_repeatable(db, monkeypatch):
    make_agent(db, "admin@cm.test", AgentRole.ADMIN)
    real = Patient(
        first_name="Real",
        last_name="Paciente",
        national_id="V1111111",
        phone="584141111111",
        email="real@gmail.com",
    )
    db.add(real)
    db.commit()

    run(monkeypatch)
    cases = list(
        db.scalars(select(Case).join(Patient).where(Patient.email.endswith("@demo.example.com")))
    )
    assert len(cases) > 100
    first_count = len(cases)

    for case in cases:
        events = list(
            db.scalars(select(CaseEvent).where(CaseEvent.case_id == case.id).order_by(CaseEvent.id))
        )
        times = [e.created_at for e in events]
        assert times == sorted(times), "los eventos van en orden cronológico"
        assert events[0].type == CaseEventType.CREATED
        stage = "registered"
        for event in events:
            if event.type == CaseEventType.STAGE_CHANGED:
                assert event.data["from"] == stage, "no hay saltos de etapa inválidos"
                stage = event.data["to"]
            elif event.type == CaseEventType.TRANSFERRED:
                stage = "registered"
        assert stage == case.stage.value, "la etapa final sale de sus eventos"
        if case.stage == CaseStage.CLOSED:
            assert case.contact_reason_id and case.closed_at
            pending = db.scalar(
                select(func.count())
                .select_from(CaseTask)
                .where(CaseTask.case_id == case.id, CaseTask.status == CaseTaskStatus.PENDING)
            )
            assert pending == 0, "no se cierra con tareas pendientes"

    assert db.scalar(select(Patient.id).where(Patient.id == real.id)) == real.id, "no toca reales"
    assert db.scalar(
        select(func.count()).select_from(Notification).where(Notification.read_at.is_(None))
    ), "deja avisos sin leer para la demostración"
    assert db.scalar(
        select(func.count()).select_from(Case).where(Case.stage == CaseStage.REGISTERED)
    )

    run(monkeypatch)  # volver a correrlo reemplaza lo anterior, no lo duplica
    assert db.scalar(select(func.count()).select_from(Case)) == first_count

    run(monkeypatch, "--purge")
    assert db.scalar(select(func.count()).select_from(Case)) == 0
    assert db.scalar(select(func.count()).select_from(Notification)) == 0
    assert db.scalar(select(func.count()).select_from(Contact)) == 0
    assert db.scalar(select(Patient.id).where(Patient.id == real.id)) == real.id
