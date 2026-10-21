import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_meta_signature
from app.db.session import get_db
from app.services import inbound

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/whatsapp", response_class=PlainTextResponse)
def verify(
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
) -> str:
    expected = get_settings().whatsapp_verify_token
    if mode == "subscribe" and expected and token == expected:
        return challenge
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Token de verificación no válido")


@router.post("/whatsapp")
async def receive(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    raw = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_meta_signature(raw, signature, get_settings().whatsapp_app_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Firma no válida")
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "JSON no válido") from exc

    inbound.process_payload(db, payload)
    return {"status": "ok"}
