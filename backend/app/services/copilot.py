"""Copiloto del agente con Gemini. Solo a pedido del agente; nunca dentro del webhook.

Antes de salir del servidor, el texto se seudonimiza: el nombre del paciente pasa a [PACIENTE] y
teléfonos, cédulas y correos a marcadores. El agente siempre revisa lo que el copiloto propone.
"""

import json
import logging
import re
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Contact, ContactReason, Conversation
from app.models.enums import SenderType
from app.services.conversations import ConversationError

logger = logging.getLogger(__name__)

PATIENT = "[PACIENTE]"

SYSTEM = (
    "Eres el copiloto de un agente de atención al paciente del Centro Médico San Bernardino "
    "(Venezuela). Escribes en español, con trato de «usted», cálido y breve. Reglas estrictas: "
    "no diagnosticas, no interpretas síntomas ni resultados y no recomiendas medicamentos ni "
    "tratamientos; si el paciente lo pide, indicas que lo valorará un médico. No inventas datos "
    "del centro (precios, horarios, coberturas, direcciones): donde haga falta uno escribe "
    "[confirmar]. Si hay señales de emergencia, indicas acudir de inmediato a Emergencia. "
    "Los marcadores entre corchetes reemplazan datos personales: consérvalos tal cual."
)

_SENDER = {
    SenderType.CONTACT: "Paciente",
    SenderType.AGENT: "Agente",
    SenderType.BOT: "Bot",
    SenderType.SYSTEM: "Sistema",
}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_CEDULA = re.compile(r"\b[VEJGvejg]\s*[-.]?\s*\d{1,2}\.?\d{3}\.?\d{3}\b")
_DOTTED_ID = re.compile(r"\b\d{1,2}\.\d{3}\.\d{3}\b")
_LONG_NUMBER = re.compile(r"\+?\d(?:[\s().-]?\d){6,}")


class CopilotUnavailableError(ConversationError):
    status_code = 503


class CopilotFailedError(ConversationError):
    status_code = 502


_ACCENTS = {"a": "aáàä", "e": "eéèë", "i": "iíìï", "o": "oóòö", "u": "uúùü", "n": "nñ"}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _loose(word: str) -> str:
    """Patrón que ignora acentos: "Maria" coincide con "María" y viceversa."""
    return "".join(
        f"[{_ACCENTS[c]}]" if c in _ACCENTS else re.escape(c) for c in _strip_accents(word).lower()
    )


def _name_pattern(contact: Contact) -> re.Pattern[str] | None:
    words = {w for w in re.split(r"\s+", contact.name or "") if len(w) >= 3}
    if not words:
        return None
    alternatives = sorted((_loose(w) for w in words), key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.IGNORECASE)


def pseudonymize(text: str, contact: Contact) -> str:
    text = _EMAIL.sub("[CORREO]", text)
    text = _CEDULA.sub("[CÉDULA]", text)
    text = _DOTTED_ID.sub("[CÉDULA]", text)
    text = _LONG_NUMBER.sub("[NÚMERO]", text)
    if pattern := _name_pattern(contact):
        text = pattern.sub(PATIENT, text)
    return text


def restore_name(text: str, contact: Contact) -> str:
    """Las propuestas vuelven al agente con el nombre de pila en lugar de [PACIENTE]."""
    first = (contact.name or "").split()[0] if contact.name else ""
    return text.replace(PATIENT, first) if first else text


def transcript(conversation: Conversation) -> str:
    settings = get_settings()
    messages = [m for m in conversation.messages if not m.is_internal_note]
    lines = [
        f"{_SENDER[m.sender_type]}: {pseudonymize(m.body, conversation.contact)}"
        for m in messages[-settings.copilot_max_messages :]
    ]
    return "\n".join(lines) or "(sin mensajes)"


def _generate(prompt: str, schema: dict[str, Any] | None = None) -> str:
    """Única salida hacia Gemini. Las pruebas la sustituyen."""
    settings = get_settings()
    if not settings.gemini_api_key:
        raise CopilotUnavailableError("El copiloto no está configurado (falta GEMINI_API_KEY)")

    from google import genai
    from google.genai import types

    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(timeout=int(settings.copilot_timeout_seconds * 1000)),
    )
    config = types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.3)
    if schema:
        config.response_mime_type = "application/json"
        config.response_json_schema = schema
    try:
        response = client.models.generate_content(
            model=settings.gemini_model, contents=prompt, config=config
        )
    except Exception as exc:
        # Solo el tipo: el mensaje de error podría contener parte del prompt.
        logger.warning(
            "copilot_error", extra={"event": "copilot_error", "error": type(exc).__name__}
        )
        raise CopilotFailedError("El copiloto no respondió. Intente de nuevo.") from None
    if not response.text:
        raise CopilotFailedError("El copiloto no devolvió una propuesta. Intente de nuevo.")
    return response.text.strip()


def summarize(conversation: Conversation) -> str:
    prompt = (
        "Resume esta conversación para otro agente en 3 a 5 viñetas cortas: qué necesita el "
        "paciente, qué se ha hecho y qué queda pendiente.\n\n" + transcript(conversation)
    )
    return _generate(prompt)


def suggest_reply(conversation: Conversation) -> str:
    prompt = (
        "Propón la próxima respuesta del agente al paciente. Devuelve solo el texto del mensaje, "
        "listo para WhatsApp, en máximo 4 oraciones.\n\n" + transcript(conversation)
    )
    return restore_name(_generate(prompt), conversation.contact)


def rewrite(conversation: Conversation, draft: str) -> str:
    prompt = (
        "Mejora la redacción de este borrador del agente: más claro, cordial y profesional, sin "
        "cambiar su contenido ni agregar información. Devuelve solo el texto final.\n\n"
        f"Contexto reciente:\n{transcript(conversation)}\n\n"
        f"Borrador:\n{pseudonymize(draft, conversation.contact)}"
    )
    return restore_name(_generate(prompt), conversation.contact)


def suggest_reason(db: Session, conversation: Conversation) -> ContactReason | None:
    reasons = list(
        db.scalars(
            select(ContactReason).where(
                ContactReason.is_active,
                (ContactReason.area_id.is_(None)) | (ContactReason.area_id == conversation.area_id),
            )
        )
    )
    if not reasons:
        return None
    catalog = "\n".join(f"{r.id}: {r.name}" for r in reasons)
    prompt = (
        "Elige el motivo de contacto que mejor describe esta conversación. Responde con el id "
        "del catálogo, o null si ninguno aplica.\n\n"
        f"Catálogo:\n{catalog}\n\nConversación:\n{transcript(conversation)}"
    )
    schema = {
        "type": "object",
        "properties": {"reason_id": {"type": ["integer", "null"]}},
        "required": ["reason_id"],
    }
    try:
        reason_id = json.loads(_generate(prompt, schema)).get("reason_id")
    except (ValueError, AttributeError):
        raise CopilotFailedError("El copiloto devolvió una respuesta no válida.") from None
    return next((r for r in reasons if r.id == reason_id), None)
