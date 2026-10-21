"""Cliente mínimo de la WhatsApp Cloud API. Sin credenciales funciona en modo simulación."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

import httpx

from app.core.config import get_settings
from app.models.enums import MessageStatus

logger = logging.getLogger(__name__)

CUSTOMER_SERVICE_WINDOW = timedelta(hours=24)
GRAPH_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class SendResult:
    external_id: str | None
    status: MessageStatus
    error_code: str | None = None


def within_service_window(last_inbound_at: datetime | None, now: datetime) -> bool:
    """Fuera de la ventana de 24 h solo se pueden enviar plantillas aprobadas."""
    return last_inbound_at is not None and now - last_inbound_at < CUSTOMER_SERVICE_WINDOW


def send_text(to: str, body: str) -> SendResult:
    return _post({"to": to, "type": "text", "text": {"body": body, "preview_url": False}})


def send_template(to: str, name: str) -> SendResult:
    """Plantilla aprobada en Meta, sin parámetros (no lleva datos del paciente)."""
    language = get_settings().whatsapp_template_language
    return _post(
        {"to": to, "type": "template", "template": {"name": name, "language": {"code": language}}}
    )


def _post(message: dict) -> SendResult:
    settings = get_settings()
    if settings.whatsapp_dry_run:
        return SendResult(external_id=f"sim-{uuid4().hex}", status=MessageStatus.SIMULATED)

    url = (
        f"https://graph.facebook.com/{settings.whatsapp_graph_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    payload = {"messaging_product": "whatsapp", "recipient_type": "individual", **message}
    try:
        response = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
            timeout=GRAPH_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError:
        logger.warning("whatsapp_send_error", extra={"event": "whatsapp_send_error"})
        return SendResult(external_id=None, status=MessageStatus.FAILED, error_code="network")

    if response.status_code >= 400:
        code = str(response.json().get("error", {}).get("code", response.status_code))
        logger.warning(
            "whatsapp_send_failed",
            extra={"event": "whatsapp_send_failed", "status_code": response.status_code},
        )
        return SendResult(external_id=None, status=MessageStatus.FAILED, error_code=code)

    wamid = response.json()["messages"][0]["id"]
    return SendResult(external_id=wamid, status=MessageStatus.SENT)
