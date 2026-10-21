from collections.abc import Callable
from datetime import timedelta

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Agent
from app.models.enums import AgentRole

LAST_SEEN_RESOLUTION = timedelta(seconds=60)


def current_agent(request: Request, db: Session = Depends(get_db)) -> Agent:
    token = request.cookies.get(get_settings().session_cookie_name)
    agent_id = decode_access_token(token) if token else None
    agent = db.get(Agent, agent_id) if agent_id else None
    if agent is None or not agent.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida")

    now = utcnow()
    if agent.last_seen_at is None or now - agent.last_seen_at > LAST_SEEN_RESOLUTION:
        agent.last_seen_at = now
        db.commit()
    return agent


def require_role(*roles: AgentRole) -> Callable[..., Agent]:
    def dependency(agent: Agent = Depends(current_agent)) -> Agent:
        if agent.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permisos para esta acción")
        return agent

    return dependency


require_supervisor = require_role(AgentRole.SUPERVISOR, AgentRole.ADMIN)
require_admin = require_role(AgentRole.ADMIN)
