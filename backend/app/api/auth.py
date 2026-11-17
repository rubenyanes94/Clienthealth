from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import current_agent
from app.core.config import get_settings
from app.core.permissions import permissions_of
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import Agent
from app.schemas import (
    AgentOut,
    LoginIn,
    MeOut,
    PasswordChangeIn,
    ResetConfirmIn,
    ResetRequestIn,
    ResetTokenIn,
    ResetTokenOut,
)
from app.services import accounts

router = APIRouter(prefix="/auth", tags=["auth"])


def to_me(agent: Agent) -> MeOut:
    return MeOut.model_validate(
        {
            **AgentOut.model_validate(agent).model_dump(),
            "permissions": sorted(permissions_of(agent.role)),
        }
    )


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


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> MeOut:
    agent = db.scalar(select(Agent).where(func.lower(Agent.email) == body.email.lower()))
    if (
        agent is None
        or not agent.is_active
        or not verify_password(body.password, agent.password_hash)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")
    _set_session_cookie(response, create_access_token(agent.id, agent.session_version))
    return to_me(agent)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(
        get_settings().session_cookie_name, path="/", secure=True, httponly=True, samesite="strict"
    )


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: PasswordChangeIn,
    response: Response,
    agent: Agent = Depends(current_agent),
    db: Session = Depends(get_db),
) -> None:
    """Cada persona pone su propia clave: lo que se haga con su cuenta solo pudo hacerlo ella.

    Cierra las demás sesiones abiertas y renueva la de este dispositivo.
    """
    if not verify_password(body.current_password, agent.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contraseña actual no es correcta")
    accounts.set_password(agent, body.new_password)
    db.commit()
    _set_session_cookie(response, create_access_token(agent.id, agent.session_version))


@router.post("/password-reset/request", status_code=status.HTTP_204_NO_CONTENT)
def request_password_reset(body: ResetRequestIn, db: Session = Depends(get_db)) -> None:
    """«¿Olvidó su contraseña?». Responde igual exista o no la cuenta, para no revelar correos."""
    accounts.request_reset(db, body.email)


@router.post("/password-reset/verify", response_model=ResetTokenOut)
def verify_reset_token(body: ResetTokenIn, db: Session = Depends(get_db)) -> ResetTokenOut:
    """POST y no GET: el enlace no debe quedar en la URL de ninguna petición ni en los registros."""
    row = accounts.check(db, body.token)
    return ResetTokenOut(purpose=row.purpose, name=row.agent.name, email=row.agent.email)


@router.post("/password-reset/confirm", response_model=MeOut)
def confirm_password_reset(
    body: ResetConfirmIn, response: Response, db: Session = Depends(get_db)
) -> MeOut:
    """Crea o cambia la contraseña con el enlace y deja la sesión iniciada."""
    agent = accounts.confirm(db, body.token, body.new_password)
    _set_session_cookie(response, create_access_token(agent.id, agent.session_version))
    return to_me(agent)


@router.get("/me", response_model=MeOut)
def me(agent: Agent = Depends(current_agent)) -> MeOut:
    return to_me(agent)
