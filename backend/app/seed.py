"""Datos iniciales: áreas, motivos, preguntas frecuentes y el agente administrador.

Idempotente. Uso: python -m app.seed  (ADMIN_EMAIL y ADMIN_PASSWORD por variables de entorno).
Los catálogos son provisionales hasta que el centro confirme los definitivos (§16).
"""

import os
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import Agent, Area, ContactReason, FaqEntry
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
