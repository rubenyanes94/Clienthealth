"""Genera 14 días de actividad ficticia para ver los paneles y hacer la demostración.

Uso:  python -m scripts.demo_data           (borra lo anterior y crea todo de nuevo)
      python -m scripts.demo_data --purge   (borra solo lo que creó este script)

Crea conversaciones de WhatsApp, pacientes, casos entre áreas (con transferencias, esperas, notas
y tareas), notificaciones y un estado «en vivo» (casos por atender, algunos fuera de meta, tareas
pendientes y avisos sin leer para el administrador). Se niega a correr en producción.

Cómo se reconoce lo que es de demostración, para poder borrarlo sin tocar datos reales:
contactos con wa_id que empieza por 5899 y pacientes con correo @demo.example.com.
"""

import random
import sys
import unicodedata
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import get_sessionmaker
from app.models import (
    Agent,
    Area,
    Case,
    CaseEvent,
    CaseNote,
    CaseTask,
    Contact,
    ContactReason,
    Conversation,
    ConversationEvent,
    Message,
    Notification,
    Patient,
    PatientEvent,
    Survey,
)
from app.models.enums import (
    AgentRole,
    CaseEventType,
    CaseStage,
    CaseTaskStatus,
    CaseTaskType,
    ConversationStatus,
    EventType,
    MessageDirection,
    MessageStatus,
    NotificationType,
    PatientEventType,
    Priority,
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
    ("Mariana Soto", "hospitalizacion"),
]
DEMO_PASSWORD = "demo-clave-123"  # noqa: S105 (clave de demostración, no es un secreto)
DEMO_EMAIL_DOMAIN = "@demo.example.com"
HOURLY_WEIGHT = [0, 0, 0, 0, 0, 1, 2, 5, 9, 10, 9, 8, 6, 6, 8, 8, 7, 5, 4, 3, 2, 2, 1, 0]


def purge(db) -> None:
    patient_ids = select(Patient.id).where(Patient.email.endswith(DEMO_EMAIL_DOMAIN))
    case_ids = select(Case.id).where(Case.patient_id.in_(patient_ids))
    db.execute(delete(Notification).where(Notification.case_id.in_(case_ids)))
    db.execute(delete(CaseTask).where(CaseTask.case_id.in_(case_ids)))
    db.execute(delete(CaseEvent).where(CaseEvent.case_id.in_(case_ids)))
    db.execute(delete(CaseNote).where(CaseNote.case_id.in_(case_ids)))
    db.execute(delete(Case).where(Case.id.in_(case_ids)))
    db.execute(delete(PatientEvent).where(PatientEvent.patient_id.in_(patient_ids)))
    db.execute(delete(Patient).where(Patient.id.in_(patient_ids)))
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
                    password_hash=hash_password(DEMO_PASSWORD),
                    password_set_at=utcnow(),
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
        generate_nps(db, now)
        generate_cases(db, areas, reasons, agents, now)


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


# --- Encuesta NPS --------------------------------------------------------------------------------


def generate_nps(db, now) -> None:
    """Respuestas de la encuesta de recomendación (0 a 10) repartidas en las dos semanas."""
    rng = random.Random(13)  # noqa: S311 (datos ficticios reproducibles)
    chats = db.execute(
        select(Conversation.id, Conversation.contact_id, Conversation.closed_at)
        .join(Contact, Contact.id == Conversation.contact_id)
        .where(Contact.wa_id.startswith(PREFIX), Conversation.closed_at.is_not(None))
        .order_by(Conversation.id)
    ).all()
    answered = 0
    for conversation_id, contact_id, closed_at in rng.sample(chats, min(70, len(chats))):
        sent = closed_at + timedelta(hours=rng.randint(2, 48))
        if sent > now - timedelta(hours=1):
            continue
        survey = Survey(
            conversation_id=conversation_id,
            contact_id=contact_id,
            kind=SurveyKind.NPS,
            status=SurveyStatus.SENT,
            sent_at=sent,
        )
        if rng.random() < 0.75:  # no todos responden
            survey.status = SurveyStatus.ANSWERED
            survey.score = rng.choices(range(11), [2, 1, 1, 2, 2, 4, 6, 9, 14, 22, 37])[0]
            survey.answered_at = min(sent + timedelta(minutes=rng.randint(3, 600)), now)
            answered += 1
        db.add(survey)
    db.commit()
    print(f"{answered} respuestas de NPS de demostración creadas")


# --- Pacientes, casos, tareas y notificaciones ---------------------------------------------------

FIRST_NAMES = [
    "Ana", "Luis", "Carmen", "José", "María", "Carlos", "Rosa", "Pedro", "Elena", "Jorge", "Lucía",
    "Miguel", "Sofía", "Andrés", "Valentina", "Daniel", "Isabel", "Fernando", "Patricia", "Héctor",
    "Gabriela", "Raúl", "Beatriz", "Oscar",
]  # fmt: skip
LAST_NAMES = [
    "Rodríguez", "Hernández", "González", "Pérez", "Martínez", "García", "López", "Sánchez",
    "Ramírez", "Torres", "Flores", "Díaz", "Morales", "Rojas", "Castillo", "Mendoza", "Silva",
    "Navarro", "Paredes", "Aguilar", "Salazar", "Medina", "Ortega", "Delgado",
]  # fmt: skip
SUBJECTS = {
    "atencion-paciente": [
        "Consulta sobre horarios de atención",
        "Solicitud de constancia de atención",
        "Reclamo por tiempo de espera en sala",
        "Felicitación al personal de enfermería",
        "Cambio de datos personales en la ficha",
    ],
    "laboratorio": [
        "Resultados de laboratorio retrasados",
        "Duda sobre la preparación para un examen",
        "Corrección de datos en un informe",
        "Solicitud de copia de resultados",
    ],
    "imagenologia": [
        "Informe de ecografía pendiente de entrega",
        "Solicitud de copia de estudio en disco",
        "Duda sobre la entrega de resultados",
    ],
    "seguros-facturacion": [
        "Carta aval pendiente de aprobación",
        "Aclaratoria de una factura",
        "Presupuesto para un procedimiento",
        "Trámite de reembolso de seguro",
        "Solicitud de copia de factura",
    ],
    "hospitalizacion": [
        "Información de visita a paciente hospitalizado",
        "Gestión del alta administrativa",
        "Presupuesto de hospitalización",
    ],
}
AREA_WEIGHTS = {
    "atencion-paciente": 30,
    "laboratorio": 22,
    "imagenologia": 14,
    "seguros-facturacion": 22,
    "hospitalizacion": 12,
}
CASE_NOTES = [
    "Se llamó al paciente y no contestó; se intentará de nuevo.",
    "Documentación recibida por correo.",
    "Se confirmó la información con el área.",
    "El paciente quedó conforme con la respuesta.",
    "Se pidió al área una respuesta para hoy.",
]
TASK_NOTES = [
    "Confirmar que recibió la información.",
    "Avisar que el documento está listo.",
    "Preguntar si quedó conforme con la atención.",
    "",
]


def _ascii(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


class Ctx:
    """Lo que comparten los generadores: catálogos, personal y contadores."""

    def __init__(self, rng, db, areas, reasons, agents, now):
        self.rng, self.db, self.areas, self.now = rng, db, areas, now
        self.area_by_id = {a.id: a for a in areas.values()}
        self.reasons = [r for r in reasons if r.name != "Urgencia derivada a Emergencia"]
        self.agents = agents
        self.admin = db.scalar(
            select(Agent).where(Agent.role == AgentRole.ADMIN, Agent.is_active).order_by(Agent.id)
        )
        names = [(f, last) for f in FIRST_NAMES for last in LAST_NAMES]
        rng.shuffle(names)
        self.names = names
        self.patient_count = 0
        self.patients: list[Patient] = []

    def agent_for(self, area_id):
        local = [a for a in self.agents if a.area_id == area_id]
        return self.rng.choice(local or self.agents)

    def other_area(self, area_id):
        return self.rng.choice([a for a in self.areas.values() if a.id != area_id])

    def reason_for(self, area_id):
        fits = [r for r in self.reasons if r.area_id in (None, area_id)]
        return self.rng.choice(fits)

    def pick_area(self):
        slug = self.rng.choices(list(AREA_WEIGHTS), list(AREA_WEIGHTS.values()))[0]
        return self.areas[slug]


def new_patient(ctx, at, creator, name=None, contact=None) -> Patient:
    ctx.patient_count += 1
    k = ctx.patient_count
    first, last = name or ctx.names.pop()
    patient = Patient(
        first_name=first,
        last_name=last,
        national_id=f"V9900{k:04d}",  # fuera del rango real de cédulas
        phone=f"584140000{k:03d}",  # el abonado empieza en 0: no puede ser un número real
        email=f"{_ascii(first.split()[0])}.{_ascii(last.split()[0])}{k}{DEMO_EMAIL_DOMAIN}",
        contact_id=contact.id if contact else None,
        created_by_agent_id=creator.id,
        created_at=at,
        updated_at=at,
    )
    ctx.db.add(patient)
    ctx.db.flush()
    ctx.db.add(
        PatientEvent(
            patient_id=patient.id, type=PatientEventType.CREATED, agent_id=creator.id, created_at=at
        )
    )
    ctx.patients.append(patient)
    return patient


def notify(ctx, recipient, actor, kind, case, task, at) -> None:
    """Igual que el servicio: a uno mismo no se le avisa. Lo reciente queda sin leer."""
    if recipient.id == actor.id:
        return
    unread = ctx.now - at < timedelta(hours=3)
    ctx.db.add(
        Notification(
            recipient_agent_id=recipient.id,
            actor_agent_id=actor.id,
            type=kind,
            case_id=case.id,
            task_id=task.id if task else None,
            created_at=at,
            read_at=None if unread else at + timedelta(minutes=ctx.rng.randint(2, 90)),
        )
    )


def random_plan(rng) -> dict:
    return {
        "attend": rng.choice([1, 2, 3, 3, 5, 5, 8, 10, 12, 14, 18, 25, 40]),
        "transfer": rng.random() < 0.12,
        "wait": (rng.randint(10, 40), rng.randint(20, 180)) if rng.random() < 0.25 else None,
        "tasks": rng.choices([0, 1, 2], [55, 35, 10])[0],
        "notes": rng.choices([0, 1, 2], [60, 30, 10])[0],
        "resolve": rng.randint(15, 240),
        "close": None if rng.random() < 0.06 else rng.randint(5, 90),
        "reopen": rng.random() < 0.04,
        "pending": [],
        "assign_to": None,
        "priority": Priority.HIGH if rng.random() < 0.08 else Priority.NORMAL,
    }


def build_case(ctx, start, area, creator, patient, plan, conversation=None) -> Case:
    """Recorre la vida del caso mientras el tiempo lo permita y deja los eventos en orden."""
    db, rng, now = ctx.db, ctx.rng, ctx.now
    case = Case(
        patient_id=patient.id,
        area_id=area.id,
        conversation_id=conversation.id if conversation else None,
        created_by_agent_id=creator.id,
        subject=rng.choice(SUBJECTS[area.slug]),
        description="Solicitud registrada para la demostración.",
        priority=plan["priority"],
        opened_at=start,
        stage_changed_at=start,
        updated_at=start,
    )
    db.add(case)
    db.flush()
    events: list[tuple] = []
    state = {"t": start, "attender": None, "pending": 0, "last_finish": start}

    def can(at) -> bool:
        return at <= now - timedelta(minutes=1)

    def ev(kind, at, agent, **data) -> None:
        events.append((at, kind, agent.id if agent else None, case.area_id, data))

    def move(stage, at, agent) -> None:
        ev(CaseEventType.STAGE_CHANGED, at, agent, **{"from": case.stage.value, "to": stage.value})
        case.stage, case.stage_changed_at = stage, at
        state["t"] = at

    def attend(minutes) -> bool:
        at = state["t"] + timedelta(minutes=minutes)
        if not can(at):
            return False
        agent = ctx.agent_for(case.area_id)
        state["attender"] = agent
        move(CaseStage.IN_PROGRESS, at, agent)
        case.assigned_agent_id = agent.id
        return True

    def add_task(assignee, at, kind, priority, notes) -> CaseTask:
        task = CaseTask(
            case_id=case.id,
            type=kind,
            priority=priority,
            notes=notes,
            assigned_agent_id=assignee.id,
            created_by_agent_id=state["attender"].id,
            created_at=at,
        )
        db.add(task)
        db.flush()
        ev(
            CaseEventType.TASK_CREATED,
            at,
            state["attender"],
            task_id=task.id,
            task_type=kind.value,
            assigned_agent_id=assignee.id,
        )
        notify(ctx, assignee, state["attender"], NotificationType.TASK_ASSIGNED, case, task, at)
        return task

    def finish() -> Case:
        events.sort(key=lambda e: e[0])  # estable: los empates conservan su orden
        for at, kind, agent_id, area_id, data in events:
            db.add(
                CaseEvent(
                    case_id=case.id,
                    type=kind,
                    agent_id=agent_id,
                    area_id=area_id,
                    data=data,
                    created_at=at,
                )
            )
        case.updated_at = max(e[0] for e in events)
        db.flush()
        return case

    ev(CaseEventType.CREATED, start, creator, area_id=area.id)

    if plan["assign_to"] is not None:  # asignado a una persona antes de que lo atiendan
        person, after = plan["assign_to"]
        at = start + timedelta(minutes=after)
        if can(at):
            case.assigned_agent_id = person.id
            ev(CaseEventType.ASSIGNED, at, creator, assigned_agent_id=person.id, from_agent_id=None)
            notify(ctx, person, creator, NotificationType.CASE_ASSIGNED, case, None, at)

    if plan["attend"] is None or not attend(plan["attend"]):
        return finish()

    if plan["transfer"]:
        at = state["t"] + timedelta(minutes=rng.randint(5, 30))
        if can(at):
            target, from_area = ctx.other_area(case.area_id), case.area_id
            case.area_id = target.id
            ev(
                CaseEventType.TRANSFERRED,
                at,
                state["attender"],
                from_area_id=from_area,
                to_area_id=target.id,
                from_stage="in_progress",
            )
            case.assigned_agent_id, case.stage, case.stage_changed_at = (
                None,
                CaseStage.REGISTERED,
                at,
            )
            state["t"], state["attender"] = at, None
            if not attend(rng.randint(2, 20)):
                return finish()

    attender, base = state["attender"], state["t"]
    for _ in range(plan["notes"]):
        at = base + timedelta(minutes=rng.randint(3, 90))
        if can(at):
            db.add(
                CaseNote(
                    case_id=case.id,
                    agent_id=attender.id,
                    body=rng.choice(CASE_NOTES),
                    created_at=at,
                )
            )
            ev(CaseEventType.NOTE_ADDED, at, attender)

    for _ in range(plan["tasks"]):
        at = base + timedelta(minutes=rng.randint(2, 20))
        if not can(at):
            break
        assignee = rng.choice(ctx.agents)
        kind = rng.choice(list(CaseTaskType))
        priority = Priority.HIGH if rng.random() < 0.15 else Priority.NORMAL
        task = add_task(assignee, at, kind, priority, rng.choice(TASK_NOTES))
        done_at = at + timedelta(minutes=rng.randint(10, 150))
        if not can(done_at):
            state["pending"] += 1
            continue
        cancelled = rng.random() < 0.08
        task.status = CaseTaskStatus.CANCELLED if cancelled else CaseTaskStatus.DONE
        task.finished_by_agent_id, task.finished_at = assignee.id, done_at
        done_kind = CaseEventType.TASK_CANCELLED if cancelled else CaseEventType.TASK_COMPLETED
        ev(done_kind, done_at, assignee, task_id=task.id, task_type=kind.value)
        state["last_finish"] = max(state["last_finish"], done_at)

    for assignee, ago, kind, priority, notes in plan["pending"]:  # tareas pendientes «en vivo»
        at = max(now - timedelta(minutes=ago), base + timedelta(minutes=1))
        add_task(assignee, at, kind, priority, notes)
        state["pending"] += 1

    if plan["wait"]:
        after, duration = plan["wait"]
        at = state["t"] + timedelta(minutes=after)
        if can(at):
            move(CaseStage.WAITING, at, attender)
            back = None if duration is None else at + timedelta(minutes=duration)
            if back is None or not can(back):
                return finish()
            move(CaseStage.IN_PROGRESS, back, attender)

    if state["pending"] or plan["resolve"] is None:  # no se resuelve con tareas por hacer
        return finish()
    at = max(
        state["t"] + timedelta(minutes=plan["resolve"]), state["last_finish"] + timedelta(minutes=1)
    )
    if not can(at):
        return finish()
    move(CaseStage.RESOLVED, at, attender)
    case.resolved_at = at
    if plan["close"] is None:
        return finish()
    at = state["t"] + timedelta(minutes=plan["close"])
    if not can(at):
        return finish()
    case.contact_reason_id = ctx.reason_for(case.area_id).id
    move(CaseStage.CLOSED, at, attender)
    case.closed_at = at

    if plan["reopen"]:
        at = state["t"] + timedelta(hours=rng.randint(1, 36))
        if can(at):
            move(CaseStage.IN_PROGRESS, at, attender)
            case.closed_at = case.resolved_at = None
            at = state["t"] + timedelta(minutes=rng.randint(10, 90))
            if can(at):
                move(CaseStage.RESOLVED, at, attender)
                case.resolved_at = at
                at = state["t"] + timedelta(minutes=rng.randint(10, 40))
                if can(at):
                    move(CaseStage.CLOSED, at, attender)
                    case.closed_at = at
    return finish()


def generate_cases(db, areas, reasons, agents, now) -> None:
    rng = random.Random(11)  # noqa: S311 (datos ficticios reproducibles)
    ctx = Ctx(rng, db, areas, reasons, agents, now)
    tz = ZoneInfo(get_settings().timezone)
    today = now.astimezone(tz).date()
    front = ctx.agent_for(areas["atencion-paciente"].id)

    # 1) Historial de dos semanas, en horario de oficina y sin domingos.
    for back in range(13, -1, -1):
        day = today - timedelta(days=back)
        if day.weekday() == 6:
            continue
        for _ in range(rng.randint(7, 13)):
            hour = rng.choices(range(24), HOURLY_WEIGHT)[0]
            start = datetime.combine(day, datetime.min.time(), tzinfo=tz) + timedelta(
                hours=hour, minutes=rng.randint(0, 59)
            )
            if start > now - timedelta(hours=4):  # lo de hoy lo cubre el estado «en vivo»
                continue
            area = ctx.pick_area()
            creator = front if rng.random() < 0.6 else ctx.agent_for(area.id)
            reuse = ctx.patients and rng.random() < 0.4
            patient = (
                rng.choice(ctx.patients)
                if reuse
                else new_patient(ctx, start - timedelta(minutes=rng.randint(2, 30)), creator)
            )
            plan = random_plan(rng)
            if start < now - timedelta(days=1) and plan["close"] is None:
                plan["close"] = rng.randint(5, 90)  # lo viejo no se queda a medio cerrar
            build_case(ctx, start, area, creator, patient, plan)

    # 2) Casos que nacieron de un chat de WhatsApp.
    chats = db.execute(
        select(Conversation, Contact)
        .join(Contact, Contact.id == Conversation.contact_id)
        .where(Contact.wa_id.startswith(PREFIX), Conversation.area_id.is_not(None))
        .order_by(Conversation.id)
    ).all()
    for conv, contact in rng.sample(chats, min(25, len(chats))):
        start = conv.opened_at + timedelta(minutes=rng.randint(8, 30))
        if start > now - timedelta(hours=4):
            continue
        area = ctx.area_by_id[conv.area_id]
        creator = ctx.agent_for(area.id)
        first, _, last = (contact.name or "Paciente Demo").partition(" ")
        patient = new_patient(ctx, start, creator, (first, last or "Demo"), contact)
        case = build_case(ctx, start, area, creator, patient, random_plan(rng), conv)
        db.add(
            PatientEvent(
                patient_id=patient.id,
                type=PatientEventType.CONTACT_LINKED,
                agent_id=creator.id,
                created_at=start,
            )
        )
        db.add(
            ConversationEvent(
                conversation_id=conv.id,
                type=EventType.CASE_CREATED,
                agent_id=creator.id,
                area_id=conv.area_id,
                data={"case_id": case.id},
                created_at=start,
            )
        )

    # 3) Estado «en vivo»: relativo a ahora, para que la demostración siempre tenga qué mostrar.
    admin = ctx.admin
    daniela = next((a for a in agents if a.email == "daniela@demo.local"), agents[0])

    def live(age, slug, **over) -> None:
        plan = {**random_plan(rng), "transfer": False, "wait": None, "tasks": 0, "notes": 1}
        plan.update(attend=None, resolve=None, close=None, reopen=False, priority=Priority.NORMAL)
        plan.update(over)
        area = areas[slug]
        creator = front
        patient = new_patient(ctx, now - timedelta(minutes=age + 5), creator)
        build_case(ctx, now - timedelta(minutes=age), area, creator, patient, plan)

    for age, slug, over in [
        (4, "atencion-paciente", {}),
        (9, "laboratorio", {}),
        (13, "seguros-facturacion", {"assign_to": (admin, 1)} if admin else {}),
        (21, "laboratorio", {"priority": Priority.HIGH}),
        (34, "imagenologia", {"assign_to": (admin, 2)} if admin else {}),
        (58, "atencion-paciente", {"priority": Priority.HIGH}),
    ]:
        live(age, slug, **over)  # por atender; los de más de 15 min ya están fuera de meta

    recipient = admin or daniela
    for age, slug, pending in [
        (
            40,
            "atencion-paciente",
            [
                (
                    recipient,
                    25,
                    CaseTaskType.CALL,
                    Priority.HIGH,
                    "Confirmar que recibió la información.",
                )
            ],
        ),
        (
            95,
            "seguros-facturacion",
            [
                (
                    recipient,
                    50,
                    CaseTaskType.WHATSAPP,
                    Priority.NORMAL,
                    "Avisar que el documento está listo.",
                ),
                (daniela, 45, CaseTaskType.EMAIL, Priority.NORMAL, ""),
            ],
        ),
        (
            160,
            "laboratorio",
            [
                (
                    recipient,
                    70,
                    CaseTaskType.EMAIL,
                    Priority.NORMAL,
                    "Enviar la copia de los resultados.",
                )
            ],
        ),
        (250, "hospitalizacion", []),
    ]:
        live(age, slug, attend=6, pending=pending)
    live(150, "imagenologia", attend=5, wait=(20, None))
    live(420, "seguros-facturacion", attend=5, wait=(30, None))
    live(210, "laboratorio", attend=4, resolve=35)
    live(470, "atencion-paciente", attend=4, resolve=30)

    db.commit()
    stages = {
        s: db.scalar(select(func.count()).select_from(Case).where(Case.stage == s))
        for s in CaseStage
    }
    print(f"{ctx.patient_count} pacientes y {sum(stages.values())} casos de demostración creados")
    print("  por etapa:", ", ".join(f"{s.value} {n}" for s, n in stages.items()))
    print(
        "  tareas:",
        db.scalar(select(func.count()).select_from(CaseTask)),
        "· notificaciones sin leer:",
        db.scalar(
            select(func.count()).select_from(Notification).where(Notification.read_at.is_(None))
        ),
    )
    print(f"  personal (contraseña «{DEMO_PASSWORD}»): daniela@demo.local, ricardo@demo.local…")
    if admin is None:
        print("  aviso: no hay administrador; no se crearon tareas ni avisos para él")


if __name__ == "__main__":
    main()
