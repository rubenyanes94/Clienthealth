from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_agent
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Agent, Contact, Conversation
from app.schemas import ContactConsentIn, ContactOut
from app.services import conversations as svc

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.put("/{contact_id}/consent", response_model=ContactOut)
def set_consent(
    contact_id: int,
    body: ContactConsentIn,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> Contact:
    """Registra (o retira) el consentimiento para mensajes proactivos, como la NPS."""
    contact = db.get(Contact, contact_id)
    conversations = db.scalars(select(Conversation).where(Conversation.contact_id == contact_id))
    if contact is None or not any(svc.can_view(agent, c) for c in conversations):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contacto no encontrado")
    if body.opt_in and contact.opt_in_at is None:
        contact.opt_in_at = utcnow()
        contact.opt_in_by_agent_id = agent.id
    elif not body.opt_in:
        contact.opt_in_at = None
        contact.opt_in_by_agent_id = agent.id
    db.commit()
    return contact
