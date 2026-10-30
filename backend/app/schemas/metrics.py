from datetime import date, time

from pydantic import BaseModel, Field, model_validator


class Ratio(BaseModel):
    value: float | None
    numerator: int
    denominator: int


class Durations(BaseModel):
    """Minutos hábiles."""

    count: int
    avg: float | None
    median: float | None
    p90: float | None


class CsatSummary(BaseModel):
    responses: int
    sent: int
    response_rate: Ratio
    avg: float | None
    satisfied: Ratio


class NpsSummary(BaseModel):
    responses: int
    promoters: int
    passives: int
    detractors: int
    score: float | None


class Overview(BaseModel):
    conversations: int
    episodes: int
    urgent: int
    first_response: Durations
    sla: Ratio
    resolution_time: Durations
    resolution_rate: Ratio
    fcr: Ratio
    reopen_rate: Ratio
    transfer_rate: Ratio
    abandon_rate: Ratio
    bot_containment: Ratio
    csat: CsatSummary
    nps: NpsSummary


class OverviewOut(Overview):
    date_from: date
    date_to: date


class HourRow(BaseModel):
    hour: int
    inbound_messages: int
    episodes: int
    first_response_median: float | None
    sla: Ratio


class AreaRow(Overview):
    area_id: int | None
    name: str


class AgentRow(BaseModel):
    agent_id: int
    name: str
    accepted: int
    first_response: Durations
    closed: int
    resolution_time: Durations
    fcr: Ratio
    csat: CsatSummary


class ReasonRow(BaseModel):
    reason_id: int | None
    name: str
    count: int
    share: float | None


class CsatDay(BaseModel):
    day: date
    responses: int
    avg: float | None
    satisfied: float | None


# --- Módulo de Casos -------------------------------------------------------------------------


class CaseTimes(BaseModel):
    """Por paso del caso por un área. Minutos hábiles."""

    received: int
    closed: int
    time_to_attention: Durations
    goal: Ratio
    attention_time: Durations
    waiting_time: Durations


class CaseOverview(CaseTimes):
    date_from: date
    date_to: date
    goal_minutes: int
    created: int
    urgent: int
    resolution_time: Durations
    resolution_rate: Ratio
    transfer_rate: Ratio
    reopen_rate: Ratio


class CaseAreaRow(CaseTimes):
    area_id: int
    name: str


class CaseAgentRow(BaseModel):
    agent_id: int
    name: str
    attended: int
    resolved: int
    closed: int
    transferred: int
    attention_time: Durations


# --- Calendario hábil ------------------------------------------------------------------------


class Slot(BaseModel):
    weekday: int = Field(ge=0, le=6)
    opens_at: time
    closes_at: time

    @model_validator(mode="after")
    def _order(self) -> "Slot":
        if self.closes_at <= self.opens_at:
            raise ValueError("La hora de cierre debe ser posterior a la de apertura")
        return self


class ScheduleOut(BaseModel):
    area_id: int | None
    inherits_default: bool
    slots: list[Slot]


class ScheduleIn(BaseModel):
    slots: list[Slot]


class HolidayIn(BaseModel):
    day: date
    name: str = Field(min_length=2, max_length=120)
    area_id: int | None = None


class HolidayOut(HolidayIn):
    id: int
