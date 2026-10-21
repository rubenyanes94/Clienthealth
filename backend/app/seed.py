"""Datos iniciales: áreas, motivos, preguntas frecuentes y el agente administrador.

Idempotente. Uso: python -m app.seed  (ADMIN_EMAIL y ADMIN_PASSWORD por variables de entorno).
Los catálogos son provisionales hasta que el centro confirme los definitivos (§16).
"""

import os
import sys
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import Agent, Area, BusinessHours, ContactReason, FaqEntry, Holiday
from app.models.enums import AgentRole

AREAS = [
    # (nombre, slug, por defecto, minutos SLA 1ª respuesta)
    ("Atención al paciente", "atencion-paciente", True, 10),
    ("Laboratorio", "laboratorio", False, 15),
    ("Imagenología", "imagenologia", False, 15),
    ("Seguros y facturación", "seguros-facturacion", False, 20),
    ("Hospitalización", "hospitalizacion", False, 15),
]

REASONS = [
    "Información general",
    "Resultados de laboratorio",
    "Resultados de imagenología",
    "Presupuesto o costos",
    "Seguros y cartas aval",
    "Facturación",
    "Información de hospitalización",
    "Reclamo",
    "Sugerencia o felicitación",
    "Urgencia derivada a Emergencia",
    "Otro",
]

FAQS = [
    (
        "Horario de atención",
        "[Texto provisional: el centro debe confirmar el horario oficial de atención por este "
        "canal y de la Emergencia.]",
    ),
    (
        "Ubicación y cómo llegar",
        "Puede consultar la dirección y el mapa en nuestra página web oficial. "
        "Si necesita indicaciones, un agente le puede ayudar.",
    ),
    (
        "Seguros aceptados",
        "Para confirmar si atendemos su póliza, elija «Seguros y facturación» en el menú y un "
        "agente lo verificará.",
    ),
    (
        "Entrega de resultados",
        "Los resultados se entregan según el tipo de estudio. Para consultar el estado de los "
        "suyos, elija «Laboratorio» o «Imagenología» en el menú y un agente le ayudará.",
    ),
]


# Horario por defecto PROVISIONAL (hora de Caracas): lunes a viernes 7–19, sábado 7–13.
DEFAULT_HOURS = [(d, time(7), time(19)) for d in range(5)] + [(5, time(7), time(13))]

# Feriados nacionales de Venezuela (Carnaval y Semana Santa varían cada año). A confirmar (§16).
HOLIDAYS = [
    (date(2026, 1, 1), "Año Nuevo"),
    (date(2026, 2, 16), "Carnaval"),
    (date(2026, 2, 17), "Carnaval"),
    (date(2026, 4, 2), "Jueves Santo"),
    (date(2026, 4, 3), "Viernes Santo"),
    (date(2026, 4, 19), "Declaración de la Independencia"),
    (date(2026, 5, 1), "Día del Trabajador"),
    (date(2026, 6, 24), "Batalla de Carabobo"),
    (date(2026, 7, 5), "Día de la Independencia"),
    (date(2026, 7, 24), "Natalicio de Simón Bolívar"),
    (date(2026, 10, 12), "Día de la Resistencia Indígena"),
    (date(2026, 12, 25), "Navidad"),
    (date(2027, 1, 1), "Año Nuevo"),
    (date(2027, 2, 8), "Carnaval"),
    (date(2027, 2, 9), "Carnaval"),
    (date(2027, 3, 25), "Jueves Santo"),
    (date(2027, 3, 26), "Viernes Santo"),
    (date(2027, 4, 19), "Declaración de la Independencia"),
    (date(2027, 5, 1), "Día del Trabajador"),
    (date(2027, 6, 24), "Batalla de Carabobo"),
    (date(2027, 7, 5), "Día de la Independencia"),
    (date(2027, 7, 24), "Natalicio de Simón Bolívar"),
    (date(2027, 10, 12), "Día de la Resistencia Indígena"),
    (date(2027, 12, 25), "Navidad"),
]


def seed(db: Session, admin_email: str | None, admin_password: str | None) -> None:
    for i, (name, slug, is_default, sla) in enumerate(AREAS):
        if db.scalar(select(Area).where(Area.slug == slug)) is None:
            db.add(
                Area(
                    name=name,
                    slug=slug,
                    is_default=is_default,
                    sort_order=i,
                    sla_first_response_minutes=sla,
                )
            )
    for name in REASONS:
        if db.scalar(select(ContactReason).where(ContactReason.name == name)) is None:
            db.add(ContactReason(name=name))
    if db.scalar(select(FaqEntry.id).limit(1)) is None:
        for i, (title, answer) in enumerate(FAQS):
            db.add(FaqEntry(title=title, answer=answer, sort_order=i))

    if db.scalar(select(BusinessHours.id).limit(1)) is None:
        for weekday, opens, closes in DEFAULT_HOURS:
            db.add(BusinessHours(area_id=None, weekday=weekday, opens_at=opens, closes_at=closes))
    if db.scalar(select(Holiday.id).limit(1)) is None:
        for day, name in HOLIDAYS:
            db.add(Holiday(day=day, name=name))

    if admin_email and admin_password:
        email = admin_email.lower()
        if db.scalar(select(Agent).where(Agent.email == email)) is None:
            db.add(
                Agent(
                    name="Administrador",
                    email=email,
                    password_hash=hash_password(admin_password),
                    role=AgentRole.ADMIN,
                )
            )
    db.commit()


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if bool(email) != bool(password):
        sys.exit("Defina ADMIN_EMAIL y ADMIN_PASSWORD juntos")
    with get_sessionmaker()() as db:
        seed(db, email, password)
    print("seed ok")


if __name__ == "__main__":
    main()
