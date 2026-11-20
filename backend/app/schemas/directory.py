from datetime import datetime

from pydantic import BaseModel, Field

# --- Lo que entrega la interfaz de datos de WordPress (solo los campos que usamos) ---------------


class WpRendered(BaseModel):
    rendered: str = Field(default="", max_length=60_000)


class WpPost(BaseModel):
    id: int
    link: str = Field(default="", max_length=500)
    modified: str | None = Field(default=None, max_length=40)
    title: WpRendered
    content: WpRendered
    categories: list[int] = Field(default_factory=list, max_length=100)
    tags: list[int] = Field(default_factory=list, max_length=100)
    class_list: list[str] = Field(default_factory=list, max_length=200)


class WpTerm(BaseModel):
    id: int
    name: str = Field(max_length=200)
    slug: str = Field(default="", max_length=200)


class WpExport(BaseModel):
    """El archivo que arma el navegador (o el script) a partir de la web del centro."""

    posts: list[WpPost] = Field(max_length=5000)
    categories: list[WpTerm] = Field(default_factory=list, max_length=2000)
    tags: list[WpTerm] = Field(default_factory=list, max_length=2000)


# --- Directorio ---------------------------------------------------------------------------------


class OfficeOut(BaseModel):
    building: str | None
    floor: str | None
    office: str | None
    text: str


class PhoneOut(BaseModel):
    label: str
    number: str
    display: str
    mobile: bool


class DirectoryDoctorOut(BaseModel):
    id: int
    name: str
    display_name: str
    specialties: list[str]
    specialty_text: str | None
    offices: list[OfficeOut]
    schedule: list[str]
    by_appointment: bool
    phones: list[PhoneOut]
    emails: list[str]
    raw_lines: list[str]
    review_notes: list[str]
    source_url: str
    search_text: str


class DirectoryImportOut(BaseModel):
    created_at: datetime
    agent_name: str | None
    total: int


class DirectoryOut(BaseModel):
    doctors: list[DirectoryDoctorOut]
    last_import: DirectoryImportOut | None


class ImportChange(BaseModel):
    name: str
    notes: list[str] = []


class ImportPreview(BaseModel):
    """Lo que haría la importación. Con `apply` además queda guardado."""

    applied: bool
    total: int
    created: int
    updated: int
    unchanged: int
    removed: int
    needs_review: list[ImportChange]
    removed_names: list[str]
    skipped_posts: int  # entradas de la web que no son fichas de médicos
