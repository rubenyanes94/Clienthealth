"""Centro de notificaciones: avisos a quien recibe una tarea o un caso."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.db.base import utcnow
from app.models import Agent, Case, CaseTask, Notification
from app.models.enums import NotificationType
from app.services.conversations import NotFoundError

PAGE = 30


def notify(
    db: Session,
    recipient_id: int,
    actor: Agent,
    type: NotificationType,
    case: Case,
    task: CaseTask | None = None,
) -> Notification | None:
    """Se llama dentro de la misma transacción que la asignación. A uno mismo no se le avisa."""
    if recipient_id == actor.id:
        return None
    notification = Notification(
        recipient_agent_id=recipient_id,
        actor_agent_id=actor.id,
        type=type,
        case_id=case.id,
        task_id=task.id if task else None,
    )
    db.add(notification)
    return notification


def unread_count(db: Session, agent: Agent) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.recipient_agent_id == agent.id, Notification.read_at.is_(None))
        )
        or 0
    )


def recent(db: Session, agent: Agent) -> list[Notification]:
    return list(
        db.scalars(
            select(Notification)
            .where(Notification.recipient_agent_id == agent.id)
            .options(
                selectinload(Notification.actor),
                selectinload(Notification.case).selectinload(Case.patient),
                selectinload(Notification.task),
            )
            .order_by(Notification.id.desc())
            .limit(PAGE)
        )
    )


def mark_read(db: Session, agent: Agent, notification_id: int) -> None:
    notification = db.get(Notification, notification_id)
    # Una notificación ajena responde igual que una inexistente.
    if notification is None or notification.recipient_agent_id != agent.id:
        raise NotFoundError("Notificación no encontrada")
    if notification.read_at is None:
        notification.read_at = utcnow()
        db.commit()


def mark_all_read(db: Session, agent: Agent) -> None:
    db.execute(
        update(Notification)
        .where(Notification.recipient_agent_id == agent.id, Notification.read_at.is_(None))
        .values(read_at=utcnow())
    )
    db.commit()
