from datetime import datetime

from pydantic import BaseModel

from app.models.enums import CaseTaskType, NotificationType
from app.schemas import ORM, AgentRef


class NotificationCase(BaseModel):
    id: int
    subject: str
    patient_name: str


class NotificationOut(ORM):
    id: int
    type: NotificationType
    created_at: datetime
    read_at: datetime | None
    actor: AgentRef | None
    case: NotificationCase
    task_type: CaseTaskType | None


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]
