from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_agent
from app.db.session import get_db
from app.models import Agent
from app.schemas import CopilotReason, CopilotRewriteIn, CopilotText, ReasonRef
from app.services import conversations as svc
from app.services import copilot

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/{conversation_id}/summary", response_model=CopilotText)
def summary(
    conversation_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> CopilotText:
    return CopilotText(text=copilot.summarize(svc.get_visible(db, agent, conversation_id)))


@router.post("/{conversation_id}/suggest", response_model=CopilotText)
def suggest(
    conversation_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> CopilotText:
    return CopilotText(text=copilot.suggest_reply(svc.get_visible(db, agent, conversation_id)))


@router.post("/{conversation_id}/rewrite", response_model=CopilotText)
def rewrite(
    conversation_id: int,
    body: CopilotRewriteIn,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> CopilotText:
    conversation = svc.get_visible(db, agent, conversation_id)
    return CopilotText(text=copilot.rewrite(conversation, body.draft))


@router.post("/{conversation_id}/reason", response_model=CopilotReason)
def reason(
    conversation_id: int, agent: Agent = Depends(current_agent), db: Session = Depends(get_db)
) -> CopilotReason:
    found = copilot.suggest_reason(db, svc.get_visible(db, agent, conversation_id))
    return CopilotReason(reason=ReasonRef.model_validate(found) if found else None)
