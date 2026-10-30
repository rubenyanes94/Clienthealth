from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import current_agent
from app.db.session import get_db
from app.models import Agent, Notification
from app.schemas.notifications import NotificationCase, NotificationList, NotificationOut
from app.services import notifications as svc

router = APIRouter(prefix="/notifications", tags=["notifications"])


def to_out(n: Notification) -> NotificationOut:
    patient = n.case.patient
    return NotificationOut(
        id=n.id,
        type=n.type,
        created_at=n.created_at,
        read_at=n.read_at,
        actor=n.actor,
        case=NotificationCase(
            id=n.case.id,
            subject=n.case.subject,
            patient_name=f"{patient.first_name} {patient.last_name}",
        ),
        task_type=n.task.type if n.task else None,
    )


@router.get("", response_model=NotificationList)
def list_notifications(
    agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> NotificationList:
    return NotificationList(
        unread=svc.unread_count(db, agent),
        items=[to_out(n) for n in svc.recent(db, agent)],
    )


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all(agent: Agent = Depends(current_agent), db: Session = Depends(get_db)) -> None:
    svc.mark_all_read(db, agent)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def read_one(
    notification_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> None:
    svc.mark_read(db, agent, notification_id)
