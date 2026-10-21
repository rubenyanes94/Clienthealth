from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_agent
from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import Agent
from app.schemas import AgentOut, LoginIn

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )


@router.post("/login", response_model=AgentOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> Agent:
    agent = db.scalar(select(Agent).where(func.lower(Agent.email) == body.email.lower()))
    if (
        agent is None
        or not agent.is_active
        or not verify_password(body.password, agent.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    _set_session_cookie(response, create_access_token(agent.id))
    return agent


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(
        get_settings().session_cookie_name, path="/", secure=True, httponly=True, samesite="strict"
    )


@router.get("/me", response_model=AgentOut)
def me(agent: Agent = Depends(current_agent)) -> Agent:
    return agent
