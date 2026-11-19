"""Interpreta la ficha de un médico tal como la publica la web del centro (texto libre en párrafos).

Es tolerante: lo que no entiende no se pierde, queda en `other_lines` y la ficha se marca para
revisar. Funciones puras: se prueban con fichas fijas y se pueden mejorar y volver a aplicar.
"""

import hashlib
import html
import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field

MOBILE_CODES = {"0412", "0414", "0416", "0422", "0424", "0426"}

_P = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S | re.I)
_BR = re.compile(r"<br\s*/?>", re.I)
_TAG = re.compile(r"<[^>]+>")
_STRONG = re.compile(r"<(strong|b)\b", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_DAY = re.compile(r"\b(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bados?|domingos?)\b", re.I)
_TIME = re.compile(r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?\s?m\b\.?|p\.?\s?m\b\.?|m\b)", re.I)
_APPOINTMENT = re.compile(r"\b(previa\s+cita|con\s+cita|solo\s+con\s+cita)\b\.?", re.I)
_LOCATION = re.compile(
    r"\b(edificio|anexo|torre|piso|nivel|planta\s+baja|pb|mezzanin[ae]?|s[óo]tano|consultorio|local)\b",
    re.I,
)
_BUILDING = re.compile(
    r"\b(anexo\s+[a-z0-9]+|torre\s+[\wáéíóú]+|edificio\s+(?!anexo\b)[\wáéíóú]+(?:\s+[\wáéíóú]+)?)",
    re.I,
)
_FLOOR = re.compile(r"\b(?:piso|nivel)\s+([\wáéíóú]+)", re.I)
_FLOOR_SPECIAL = re.compile(r"\b(planta\s+baja|pb|mezzanin[ae]?|s[óo]tano(?:\s+\d+)?)\b", re.I)
_OFFICE = re.compile(r"\b(?:consultorio|local)\s*(?:n[°ºo.]*\s*)?([\w-]+)", re.I)
_PHONE_SPLIT = re.compile(r"\s+[-–—/]\s+|[–—/,;]|\s+y\s+|\s+o\s+", re.I)
_MOBILE_LABEL = re.compile(r"cel|m[óo]vil|whats", re.I)


@dataclass
class Office:
    building: str | None
    floor: str | None
    office: str | None
    text: str


@dataclass
class Phone:
    label: str
    number: str  # como se marca en Venezuela: 02125525586
    display: str  # 0212 5525586
    mobile: bool


@dataclass
class ParsedDoctor:
    specialty_text: str | None = None
    offices: list[Office] = field(default_factory=list)
    schedule: list[str] = field(default_factory=list)
    by_appointment: bool = False
    phones: list[Phone] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    other_lines: list[str] = field(default_factory=list)
    raw_lines: list[str] = field(default_factory=list)
    review_notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def clean(text: str) -> str:
    text = html.unescape(text).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:])", r"\1", text)  # «p.m .» → «p.m.»
    text = re.sub(r":(\s*:)+", ":", text)  # «Consultorio: :» → «Consultorio:»
    return text.strip(" -–")


def fold(text: str) -> str:
    """Minúsculas y sin tildes, para buscar «cardiologia» y encontrar «Cardiología»."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def paragraphs(content_html: str) -> list[tuple[str, bool]]:
    """(texto, va en negrita) de cada línea con contenido."""
    blocks = _P.findall(content_html) or [content_html]
    lines: list[tuple[str, bool]] = []
    for block in blocks:
        strong = bool(_STRONG.search(block))
        for piece in _BR.split(block):
            text = clean(_TAG.sub(" ", piece))
            if text:
                lines.append((text, strong))
    return lines


def _title(text: str) -> str:
    return " ".join(w if w.isupper() and len(w) <= 2 else w.capitalize() for w in text.split())


def parse_office(text: str) -> Office:
    building = _BUILDING.search(text)
    floor = _FLOOR.search(text)
    special = _FLOOR_SPECIAL.search(text)
    office = _OFFICE.search(text)
    floor_value = floor.group(1) if floor else None
    if floor_value is None and special:
        word = fold(special.group(1))
        floor_value = "PB" if word in ("pb", "planta baja") else _title(special.group(1))
    return Office(
        building=_title(building.group(1)) if building else None,
        floor=floor_value.upper() if floor_value and len(floor_value) <= 3 else floor_value,
        office=office.group(1).upper() if office else None,
        text=text,
    )


def _format(number: str) -> str:
    return f"{number[:4]} {number[4:]}"


def parse_phones(text: str) -> list[Phone]:
    """«Consultorio: 0212 5521886 – 5521464» → dos teléfonos; el segundo hereda el 0212."""
    label_part, _, numbers_part = text.partition(":")
    if not numbers_part:
        first_digit = re.search(r"\d", text)
        label_part = text[: first_digit.start()] if first_digit else ""
        numbers_part = text[first_digit.start() :] if first_digit else ""
    label = clean(label_part) or "Teléfono"
    phones: list[Phone] = []
    area: str | None = None
    for piece in _PHONE_SPLIT.split(numbers_part):
        digits = re.sub(r"\D", "", piece)
        if len(digits) == 12 and digits.startswith("58"):
            digits = "0" + digits[2:]
        elif len(digits) == 10 and not digits.startswith("0"):
            digits = "0" + digits
        elif len(digits) == 7 and area:
            digits = area + digits
        if len(digits) != 11 or not digits.startswith("0"):
            continue
        area = digits[:4]
        mobile = area in MOBILE_CODES
        phones.append(Phone(label=label, number=digits, display=_format(digits), mobile=mobile))
    return phones


def parse_content(content_html: str) -> ParsedDoctor:
    doctor = ParsedDoctor()
    for index, (line, strong) in enumerate(paragraphs(content_html)):
        doctor.raw_lines.append(line)
        rest = line
        emails = _EMAIL.findall(rest)
        if emails:
            doctor.emails.extend(e.lower() for e in emails)
            rest = clean(_EMAIL.sub(" ", rest))
        if _APPOINTMENT.search(rest):
            doctor.by_appointment = True
            rest = clean(_APPOINTMENT.sub(" ", rest))
        if not rest:
            continue
        if strong and index == 0 and not _LOCATION.search(rest):
            doctor.specialty_text = rest.rstrip(".")
            continue
        phones = parse_phones(rest)
        if phones:
            doctor.phones.extend(phones)
        elif _LOCATION.search(rest):
            doctor.offices.append(parse_office(rest))
        elif _DAY.search(rest) or _TIME.search(rest):
            doctor.schedule.append(rest)
        else:
            doctor.other_lines.append(rest)

    if not doctor.offices:
        doctor.review_notes.append("No se encontró la ubicación del consultorio")
    for office in doctor.offices:
        if not office.building or not office.office:
            doctor.review_notes.append(f"Ubicación incompleta: «{office.text}»")
    for line in doctor.other_lines:
        doctor.review_notes.append(f"Texto sin clasificar: «{line}»")
    doctor.emails = list(dict.fromkeys(doctor.emails))
    return doctor


def split_name(title: str) -> tuple[str, str, str]:
    """«Abecasis Salama, Nissim Moisés» → (apellidos, nombres, «Nissim Moisés Abecasis Salama»)."""
    name = clean(title)
    last, _, first = name.partition(",")
    last, first = clean(last), clean(first)
    display = f"{first} {last}".strip() if first else last
    return last, first, display


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
