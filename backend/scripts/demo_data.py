"""Genera 14 días de actividad ficticia para ver los paneles en desarrollo.

Uso:  python -m scripts.demo_data           (crea)
      python -m scripts.demo_data --purge   (borra solo lo que creó este script)

Se niega a correr en producción. Los contactos de demostración usan wa_id que empiezan con 5899.
"""

import random
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import get_sessionmaker
from app.models import (
    Agent,
    Area,
    Contact,
    ContactReason,
    Conversation,
    ConversationEvent,
    Message,
    Survey,
)
from app.models.enums import (
    AgentRole,
    ConversationStatus,
    EventType,
    MessageDirection,
    MessageStatus,
    SenderType,
    SurveyKind,
    SurveyStatus,
)

PREFIX = "5899"
NAMES = [
    "Ana Rodríguez",
    "Luis Hernández",
    "Carmen González",
    "José Pérez",
    "María Martínez",
    "Carlos García",
    "Rosa López",
    "Pedro Sánchez",
    "Elena Ramírez",
    "Jorge Torres",
    "Lucía Flores",
    "Miguel Díaz",
    "Sofía Morales",
    "Andrés Rojas",
    "Valentina Castillo",
]
AGENTS = [
    ("Daniela Ruiz", "laboratorio"),
    ("Ricardo Méndez", "atencion-paciente"),
    ("Gabriela Ortiz", "seguros-facturacion"),
    ("Tomás Vargas", "imagenologia"),
]
HOURLY_WEIGHT = [0, 0, 0, 0, 0, 1, 2, 5, 9, 10, 9, 8, 6, 6, 8, 8, 7, 5, 4, 3, 2, 2, 1, 0]


def purge(db) -> None:
    contact_ids = select(Contact.id).where(Contact.wa_id.startswith(PREFIX))
    conv_ids = select(Conversation.id).where(Conversation.contact_id.in_(contact_ids))
    db.execute(delete(Survey).where(Survey.conversation_id.in_(conv_ids)))
    db.execute(delete(ConversationEvent).where(ConversationEvent.conversation_id.in_(conv_ids)))
    db.execute(delete(Message).where(Message.conversation_id.in_(conv_ids)))
    db.execute(delete(Conversation).where(Conversation.id.in_(conv_ids)))
    db.execute(delete(Contact).where(Contact.wa_id.startswith(PREFIX)))
    db.commit()


def main() -> None:
    if get_settings().is_production:
        sys.exit("No se generan datos de demostración en producción.")
    rng = random.Random(7)  # noqa: S311 (datos ficticios reproducibles)
    with get_sessionmaker()() as db:
        purge(db)
        if "--purge" in sys.argv:
            print("datos de demostración eliminados")
            return

        areas = {a.slug: a for a in db.scalars(select(Area))}
        reasons = list(db.scalars(select(ContactReason)))
        agents = []
        for name, slug in AGENTS:
            email = name.split()[0].lower() + "@demo.local"
            agent = db.scalar(select(Agent).where(Agent.email == email))
            if agent is None:
                agent = Agent(
                    name=name,
                    email=email,
                    password_hash=hash_password("demo-clave-123"),
                    role=AgentRole.AGENT,
                    area_id=areas[slug].id,
                )
                db.add(agent)
                db.flush()
            agents.append(agent)

        tz = ZoneInfo(get_settings().timezone)
        today = utcnow().astimezone(tz).date()
        now = utcnow()
        n = 0
        for back in range(13, -1, -1):
            day = today - timedelta(days=back)
            if day.weekday() == 6:
                continue
            for _ in range(rng.randint(14, 26)):
                hour = rng.choices(range(24), HOURLY_WEIGHT)[0]
                start = datetime.combine(day, datetime.min.time(), tzinfo=tz) + timedelta(
                    hours=hour, minutes=rng.randint(0, 59)
                )
                if start > now - timedelta(minutes=30):
                    continue
                n += 1
                build_conversation(db, rng, n, start, now, areas, reasons, agents)
        db.commit()
        print(f"{n} conversaciones de demostración creadas")


def build_conversation(db, rng, n, start, now, areas, reasons, agents) -> None:
    contact = Contact(wa_id=f"{PREFIX}{n:07d}", name=rng.choice(NAMES), created_at=start)
    db.add(contact)
    db.flush()
    conv = Conversation(contact_id=contact.id, status=ConversationStatus.BOT, opened_at=start)
    db.add(conv)
    db.flush()
    t = start

    def ev(event_type, at, agent=None, **data):
        db.add(
            ConversationEvent(
                conversation_id=conv.id,
                type=event_type,
                agent_id=agent.id if agent else None,
                area_id=conv.area_id,
                data=data,
                created_at=at,
            )
        )

    def msg(direction, sender, body, at, agent=None, status=MessageStatus.SIMULATED):
        m = Message(
            conversation_id=conv.id,
            direction=direction,
            sender_type=sender,
            agent_id=agent.id if agent else None,
            body=body,
            status=status,
            created_at=at,
        )
        db.add(m)
        db.flush()
        return m

    ev(EventType.CREATED, t, channel="whatsapp")
    m = msg(
        MessageDirection.INBOUND,
        SenderType.CONTACT,
        "Hola, buenos días",
        t,
        status=MessageStatus.RECEIVED,
    )
    ev(EventType.INBOUND_MESSAGE, t, message_id=m.id)
    t += timedelta(seconds=5)
    m = msg(MessageDirection.OUTBOUND, SenderType.BOT, "Menú principal", t)
    ev(EventType.BOT_MESSAGE, t, message_id=m.id)

    if rng.random() < 0.18:  # la resuelve el bot
        t += timedelta(minutes=2)
        ev(EventType.BOT_RESOLVED, t)
        ev(EventType.CLOSED, t, by="bot", reason_id=None)
        conv.status, conv.closed_at = ConversationStatus.CLOSED, t
        conv.last_message_at = conv.updated_at = t
        return

    agent = rng.choice(agents)
    conv.area_id = agent.area_id
    urgent = rng.random() < 0.05
    t += timedelta(minutes=1)
    if urgent:
        conv.is_urgent = True
        ev(EventType.URGENCY_DETECTED, t, source="rules")
    ev(EventType.BOT_ESCALATED, t, area_id=conv.area_id, reason="urgency" if urgent else "menu")
    conv.status, conv.queued_at = ConversationStatus.QUEUED, t

    wait = timedelta(minutes=rng.choice([1, 2, 3, 4, 6, 8, 11, 14, 20, 35]))
    if t + wait > now or rng.random() < 0.04:  # sigue en cola (o se abandonó)
        conv.last_message_at = conv.updated_at = t
        return
    t += wait
    conv.status, conv.assigned_agent_id = ConversationStatus.OPEN, agent.id
    ev(EventType.ACCEPTED, t, agent, from_status="queued")
    t += timedelta(seconds=40)
    m = msg(
        MessageDirection.OUTBOUND, SenderType.AGENT, "Buenos días, con gusto le ayudo.", t, agent
    )
    ev(EventType.AGENT_MESSAGE, t, agent, message_id=m.id, status="simulated")

    if rng.random() < 0.08:
        t += timedelta(minutes=3)
        target = rng.choice([a for a in agents if a.area_id != conv.area_id])
        ev(EventType.TRANSFERRED, t, agent, from_area_id=conv.area_id, to_area_id=target.area_id)
        conv.area_id, agent = target.area_id, target
        t += timedelta(minutes=rng.randint(2, 15))
        ev(EventType.ACCEPTED, t, agent, from_status="queued")

    t += timedelta(minutes=rng.randint(3, 40))
    if t > now:
        conv.last_message_at = conv.updated_at = t - timedelta(minutes=1)
        return
    area_reasons = [r for r in reasons if r.name != "Urgencia derivada a Emergencia"]
    reason = rng.choice(area_reasons)
    conv.status, conv.closed_at, conv.contact_reason_id = ConversationStatus.CLOSED, t, reason.id
    ev(EventType.CLOSED, t, agent, by="agent", reason_id=reason.id)
    conv.last_message_at = conv.updated_at = t

    if not urgent and rng.random() < 0.7:
        survey = Survey(
            conversation_id=conv.id,
            contact_id=contact.id,
            agent_id=agent.id,
            kind=SurveyKind.CSAT,
            status=SurveyStatus.SENT,
            sent_at=t,
        )
        db.add(survey)
        db.flush()
        ev(EventType.SURVEY_SENT, t, agent, survey_id=survey.id, kind="csat")
        if rng.random() < 0.6 and t + timedelta(minutes=10) < now:
            survey.status = SurveyStatus.ANSWERED
            survey.score = rng.choices([5, 4, 3, 2, 1], [55, 25, 10, 6, 4])[0]
            survey.answered_at = t + timedelta(minutes=rng.randint(1, 10))
            ev(
                EventType.SURVEY_ANSWERED,
                survey.answered_at,
                survey_id=survey.id,
                kind="csat",
                score=survey.score,
            )


if __name__ == "__main__":
    main()
