from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_agent
from app.db.session import get_db
from app.models import Agent, Conversation
from app.schemas import CloseIn, ConversationDetail, MessageIn, MessageOut, TransferIn
from app.services import conversations as svc

router = APIRouter(prefix="/conversations", tags=["conversations"])


def detail(db: Session, conversation: Conversation) -> ConversationDetail:
    db.refresh(conversation)
    return ConversationDetail.model_validate(conversation)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> ConversationDetail:
    return ConversationDetail.model_validate(svc.get_visible(db, agent, conversation_id))


@router.post("/{conversation_id}/accept", response_model=ConversationDetail)
def accept(
    conversation_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> ConversationDetail:
    return detail(db, svc.accept(db, agent, conversation_id))


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def post_message(
    conversation_id: int,
    body: MessageIn,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
):
    return svc.post_message(
        db, agent, conversation_id, body.body, is_internal_note=body.is_internal_note
    )


@router.post("/{conversation_id}/pending", response_model=ConversationDetail)
def set_pending(
    conversation_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> ConversationDetail:
    return detail(db, svc.set_pending(db, agent, conversation_id))


@router.post("/{conversation_id}/resume", response_model=ConversationDetail)
def resume(
    conversation_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> ConversationDetail:
    return detail(db, svc.resume(db, agent, conversation_id))


@router.post("/{conversation_id}/transfer", response_model=ConversationDetail)
def transfer(
    conversation_id: int,
    body: TransferIn,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    conversation = svc.transfer(db, agent, conversation_id, body.area_id)
    db.refresh(conversation)
    # Tras transferir, un agente de otra área puede dejar de ver el caso.
    return ConversationDetail.model_validate(conversation)


@router.post("/{conversation_id}/close", response_model=ConversationDetail)
def close(
    conversation_id: int,
    body: CloseIn,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    return detail(db, svc.close(db, agent, conversation_id, body.contact_reason_id))


@router.post("/{conversation_id}/reopen", response_model=ConversationDetail)
def reopen(
    conversation_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> ConversationDetail:
    return detail(db, svc.reopen(db, agent, conversation_id))
