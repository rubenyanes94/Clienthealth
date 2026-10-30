import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.models.enums import CaseEventType, CaseStage, PatientEventType, Priority
from app.schemas import ORM, AgentRef, AreaRef, CaseBrief, PatientRef, ReasonRef


def normalize_national_id(value: str) -> str:
    """V-12.345.678 y v12345678 son la misma cédula."""
    cleaned = re.sub(r"[\s.\-]", "", value).upper()
    if not re.fullmatch(r"[A-Z0-9]{5,20}", cleaned):
        raise ValueError("Cédula no válida")
    return cleaned


def normalize_phone(value: str) -> str:
    """Solo dígitos y con código de país: 0414-1234567 pasa a 584141234567, como en WhatsApp."""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("0"):
        digits = "58" + digits[1:]
    if not 8 <= len(digits) <= 15:
        raise ValueError("Teléfono no válido")
    return digits


def _clean_name(value: str) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) < 2:
        raise ValueError("Demasiado corto")
    return cleaned


Name = Annotated[str, Field(max_length=120), AfterValidator(_clean_name)]
NationalId = Annotated[str, Field(max_length=40), AfterValidator(normalize_national_id)]
Phone = Annotated[str, Field(max_length=40), AfterValidator(normalize_phone)]


class PatientIn(BaseModel):
    first_name: Name
    last_name: Name
    national_id: NationalId
    phone: Phone
    email: EmailStr


class PatientPatch(BaseModel):
    first_name: Name | None = None
    last_name: Name | None = None
    national_id: NationalId | None = None
    phone: Phone | None = None
    email: EmailStr | None = None


class PatientOut(PatientRef):
    email: str
    contact_id: int | None
    created_at: datetime


class PatientEventOut(ORM):
    id: int
    type: PatientEventType
    agent: AgentRef | None
    data: dict[str, list[str]]
    created_at: datetime


class PatientDetail(PatientOut):
    cases: list[CaseBrief] = []
    events: list[PatientEventOut] = []


class PatientSearchIn(BaseModel):
    """Por POST: una cédula o un nombre en la URL quedarían en los logs de acceso (§12)."""

    q: str = Field(default="", max_length=120)
    cursor: str | None = None


class PatientPage(BaseModel):
    items: list[PatientOut]
    next_cursor: str | None


class CaseIn(BaseModel):
    patient_id: int
    area_id: int
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=4000)
    priority: Priority = Priority.NORMAL
    conversation_id: int | None = None


class CasePatch(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: Priority | None = None


class CaseStageIn(BaseModel):
    stage: CaseStage
    contact_reason_id: int | None = None  # obligatorio al cerrar, si el caso aún no lo tiene


class CaseTransferIn(BaseModel):
    area_id: int


class CaseNoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class CaseNoteOut(ORM):
    id: int
    agent: AgentRef | None
    body: str
    created_at: datetime


class CaseEventOut(ORM):
    id: int
    type: CaseEventType
    agent: AgentRef | None
    area_id: int | None
    data: dict[str, int | str | list[str] | None]
    created_at: datetime


class CaseSummary(ORM):
    id: int
    subject: str
    stage: CaseStage
    priority: Priority
    patient: PatientRef
    area: AreaRef
    assigned_agent: AgentRef | None
    conversation_id: int | None
    opened_at: datetime
    stage_changed_at: datetime
    updated_at: datetime


class CaseDetail(CaseSummary):
    description: str
    created_by: AgentRef | None
    contact_reason: ReasonRef | None
    resolved_at: datetime | None
    closed_at: datetime | None
    events: list[CaseEventOut]
    notes: list[CaseNoteOut]
    next_stages: list[CaseStage]
    # Si el agente no puede abrir la conversación vinculada, no se ofrece el enlace.
    can_view_conversation: bool = False


CaseStageFilter = Literal[
    "open", "all", "registered", "in_progress", "waiting", "resolved", "closed"
]


class CaseSearchIn(BaseModel):
    """Por POST, como la búsqueda de pacientes: `q` puede llevar un nombre o una cédula."""

    stage: CaseStageFilter = "open"
    area_id: int | None = None
    mine: bool = False
    q: str = Field(default="", max_length=120)
    cursor: str | None = None


class CasePage(BaseModel):
    items: list[CaseSummary]
    next_cursor: str | None
    goal_minutes: int


class StageCounts(BaseModel):
    registered: int = 0
    in_progress: int = 0
    waiting: int = 0
    resolved: int = 0
    late: int = 0  # por atender más tiempo que la meta de su área
    oldest_registered_at: datetime | None = None


class AreaLive(StageCounts):
    area: AreaRef


class CasesLive(StageCounts):
    urgent: int
    goal_minutes: int
    created_today: int
    closed_today: int
    first_attention_median: float | None
    resolution_median: float | None
    areas: list[AreaLive]
