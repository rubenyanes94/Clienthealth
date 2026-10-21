"""Clasificador de urgencia por reglas (fase 1).

Se ejecuta antes que el bot. Prefiere falsos positivos: un caso marcado como urgente por error
solo sube en la cola. La lista es provisional hasta que el centro apruebe la definitiva (§16).
"""

import re
import unicodedata

URGENCY_PHRASES: tuple[str, ...] = (
    "dolor de pecho",
    "dolor en el pecho",
    "dolor fuerte en el pecho",
    "me duele el pecho",
    "no puedo respirar",
    "no puede respirar",
    "no respira",
    "falta de aire",
    "me falta el aire",
    "me ahogo",
    "se ahoga",
    "se esta ahogando",
    "sangrado",
    "sangra mucho",
    "hemorragia",
    "vomita sangre",
    "desmayo",
    "se desmayo",
    "me desmaye",
    "desmayado",
    "desmayada",
    "convulsion",
    "convulsiones",
    "convulsionando",
    "esta convulsionando",
    "inconsciente",
    "no reacciona",
    "perdio el conocimiento",
    "infarto",
    "paro cardiaco",
    "paro respiratorio",
    "acv",
    "derrame cerebral",
    "se le durmio la cara",
    "intoxicacion",
    "envenenamiento",
    "sobredosis",
    "quemadura grave",
    "accidente",
    "me quiero morir",
    "quiero suicidarme",
    "suicidio",
    "emergencia",
)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text)).strip()


_PATTERN = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in URGENCY_PHRASES) + r")\b")


def is_urgent(text: str) -> bool:
    return bool(text) and _PATTERN.search(normalize(text)) is not None
