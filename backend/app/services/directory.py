"""Directorio de consultorios: importa las fichas de la web del centro y las interpreta.

La web solo responde desde Venezuela, así que el servidor nunca la consulta: el navegador de quien
actualiza trae los datos y los envía aquí. Este servicio valida, interpreta y guarda.
"""

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models import Agent, DirectoryDoctor, DirectoryImport
from app.schemas.directory import WpExport, WpPost
from app.services import directory_parser as parser
from app.services.conversations import ConflictError, ConversationError

UNCATEGORIZED = {"uncategorized", "sin-categoria", "sin categoría"}
# Si la importación trae mucho menos que lo que hay, probablemente se cortó: no se borra nada.
MIN_SHARE_TO_REMOVE = 0.5


@dataclass
class Plan:
    rows: list[dict] = field(default_factory=list)
    skipped: int = 0


def _letter_tags(export: WpExport) -> set[int]:
    return {
        t.id for t in export.tags if len(t.slug or t.name) == 1 and (t.slug or t.name).isalpha()
    }


def _is_doctor(post: WpPost, letter_tags: set[int]) -> bool:
    """Las fichas de médicos son las entradas con una etiqueta de una sola letra (A–Z)."""
    if letter_tags and set(post.tags) & letter_tags:
        return True
    return any(re.fullmatch(r"tag-[a-z]", c) for c in post.class_list)


def build(export: WpExport) -> Plan:
    names = {c.id: parser.clean(c.name) for c in export.categories}
    excluded = {c.id for c in export.categories if parser.fold(c.slug or c.name) in UNCATEGORIZED}
    letters = _letter_tags(export)
    plan = Plan()
    for post in export.posts:
        if not _is_doctor(post, letters):
            plan.skipped += 1
            continue
        parsed = parser.parse_content(post.content.rendered)
        last, first, display = parser.split_name(post.title.rendered)
        name = f"{last}, {first}" if first else last
        specialties = [names[c] for c in post.categories if c in names and c not in excluded]
        if not specialties and parsed.specialty_text:
            specialties = [s.strip() for s in re.split(r"[.;]", parsed.specialty_text) if s.strip()]
        data = parsed.as_dict()
        row = {
            "source_id": post.id,
            "source_url": post.link,
            "source_modified": post.modified,
            "name": name,
            "display_name": display,
            "specialties": specialties,
            "specialty_text": data["specialty_text"],
            "offices": data["offices"],
            "schedule": data["schedule"],
            "by_appointment": data["by_appointment"],
            "phones": data["phones"],
            "emails": data["emails"],
            "raw_lines": data["raw_lines"],
            "review_notes": data["review_notes"],
        }
        locations = " ".join(
            f"{o['building'] or ''} piso {o['floor'] or ''} consultorio {o['office'] or ''}"
            for o in data["offices"]
        )
        row["search_text"] = parser.fold(
            " ".join(
                [name, display, " ".join(specialties), data["specialty_text"] or "", locations]
            )
        )
        row["fingerprint"] = parser.fingerprint({k: v for k, v in row.items()})
        plan.rows.append(row)
    if not plan.rows:
        raise ConversationError(
            "El archivo no trae fichas de médicos: revise que venga de la web del centro"
        )
    return plan


def run(db: Session, agent: Agent, export: WpExport, *, apply: bool) -> dict:
    plan = build(export)
    existing = {d.source_id: d for d in db.scalars(select(DirectoryDoctor))}
    active = [d for d in existing.values() if d.is_active]
    incoming = {row["source_id"] for row in plan.rows}
    removed = [d for d in active if d.source_id not in incoming]
    if removed and len(plan.rows) < len(active) * MIN_SHARE_TO_REMOVE:
        raise ConflictError(
            f"La importación trae {len(plan.rows)} médicos y el directorio tiene {len(active)}: "
            "parece incompleta. Vuelva a traerla desde la web."
        )

    created = updated = unchanged = 0
    now = utcnow()
    for row in plan.rows:
        doctor = existing.get(row["source_id"])
        if doctor is None:
            created += 1
            if apply:
                db.add(DirectoryDoctor(**row, imported_at=now, updated_at=now))
        elif doctor.fingerprint != row["fingerprint"] or not doctor.is_active:
            updated += 1
            if apply:
                for key, value in row.items():
                    setattr(doctor, key, value)
                doctor.is_active = True
                doctor.updated_at = now
        else:
            unchanged += 1
    review = [
        {"name": row["name"], "notes": row["review_notes"]}
        for row in plan.rows
        if row["review_notes"]
    ]
    if apply:
        for doctor in removed:
            doctor.is_active = False
            doctor.updated_at = now
        db.add(
            DirectoryImport(
                agent_id=agent.id,
                created_at=now,
                total=len(plan.rows),
                created=created,
                updated=updated,
                removed=len(removed),
                needs_review=len(review),
            )
        )
        db.commit()
    return {
        "applied": apply,
        "total": len(plan.rows),
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "removed": len(removed),
        "needs_review": sorted(review, key=lambda r: r["name"]),
        "removed_names": sorted(d.name for d in removed),
        "skipped_posts": plan.skipped,
    }


def listing(db: Session) -> dict:
    doctors = db.scalars(
        select(DirectoryDoctor).where(DirectoryDoctor.is_active).order_by(DirectoryDoctor.name)
    )
    last = db.scalar(select(DirectoryImport).order_by(DirectoryImport.id.desc()).limit(1))
    return {
        "doctors": list(doctors),
        "last_import": (
            {
                "created_at": last.created_at,
                "agent_name": last.agent.name if last.agent else None,
                "total": last.total,
            }
            if last
            else None
        ),
    }
