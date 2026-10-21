from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import current_agent
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Agent, Conversation
from app.models.enums import ConversationStatus
from app.schemas import ConversationSummary, InboxChanges, InboxPage
from app.services import conversations as svc

router = APIRouter(prefix="/inbox", tags=["inbox"])

PAGE_SIZE = 50
PREVIEW_CHARS = 120
InboxFilter = Literal["open", "queue", "mine", "pending", "closed", "bot", "all"]


def summarize(db: Session, rows: list[Conversation]) -> list[ConversationSummary]:
    latest = svc.latest_messages(db, [c.id for c in rows])
    items = []
    for conversation in rows:
        item = ConversationSummary.model_validate(conversation)
        if message := latest.get(conversation.id):
            item.last_message_preview = message.body[:PREVIEW_CHARS]
            item.last_message_direction = message.direction
            item.last_message_sender = message.sender_type
        items.append(item)
    return items


@router.get("", response_model=InboxPage)
def list_inbox(
    filter: InboxFilter = "open",
    cursor: str | None = None,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> InboxPage:
    offset = int(cursor) if cursor and cursor.isdigit() else 0
    query = (
        select(Conversation)
        .where(*svc.list_filter(agent, filter))
        .options(
            selectinload(Conversation.contact),
            selectinload(Conversation.area),
            selectinload(Conversation.assigned_agent),
        )
    )
    if filter == "queue":
        # Urgentes primero; después, quien lleva más tiempo esperando.
        query = query.order_by(
            Conversation.is_urgent.desc(), Conversation.queued_at.asc(), Conversation.id
        )
    elif filter == "closed":
        query = query.order_by(Conversation.closed_at.desc().nulls_last(), Conversation.id.desc())
    else:
        queued_first = case((Conversation.status == ConversationStatus.QUEUED, 0), else_=1)
        query = query.order_by(
            Conversation.is_urgent.desc(),
            queued_first,
            Conversation.last_message_at.desc().nulls_last(),
            Conversation.id.desc(),
        )
    rows = list(db.scalars(query.offset(offset).limit(PAGE_SIZE + 1)))
    has_more = len(rows) > PAGE_SIZE
    rows = rows[:PAGE_SIZE]
    return InboxPage(
        items=summarize(db, rows), next_cursor=str(offset + PAGE_SIZE) if has_more else None
    )


@router.get("/changes", response_model=InboxChanges)
def changes(
    since: datetime = Query(..., description="ISO 8601 con zona horaria (server_time anterior)"),
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> InboxChanges:
    server_time = utcnow()
    query = select(Conversation.id).where(Conversation.updated_at > since)
    if (feed := svc.change_feed_filter(agent)) is not None:
        query = query.where(feed)
    ids = list(db.scalars(query.order_by(Conversation.updated_at.desc()).limit(200)))
    return InboxChanges(server_time=server_time, ids=ids)
