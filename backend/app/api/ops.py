"""Salud, métricas en vivo, cron y utilidades de desarrollo."""

import hmac
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import exists, func, select, text
from sqlalchemy.orm import Session, aliased

from app.api.deps import current_agent, require_supervisor
from app.core.config import get_settings
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Agent, Conversation, ConversationEvent
from app.models.enums import ConversationStatus, EventType
from app.schemas import HealthOut, LiveMetrics, SimulateInboundIn
from app.services import events, inbound, surveys

router = APIRouter(tags=["ops"])

ONLINE_WINDOW = timedelta(minutes=5)


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "error"
    return HealthOut(
        status="ok" if database == "ok" else "degraded",
        database=database,
        environment=settings.environment,
        whatsapp_dry_run=settings.whatsapp_dry_run,
    )


@router.get("/metrics/live", response_model=LiveMetrics)
def live_metrics(_: Agent = Depends(current_agent), db: Session = Depends(get_db)) -> LiveMetrics:
    counts = dict(
        db.execute(
            select(Conversation.status, func.count())
            .where(Conversation.status != ConversationStatus.CLOSED)
            .group_by(Conversation.status)
        ).all()
    )
    queued = select(Conversation).where(Conversation.status == ConversationStatus.QUEUED)
    oldest = db.scalar(
        select(func.min(Conversation.queued_at)).where(
            Conversation.status == ConversationStatus.QUEUED
        )
    )
    urgent = db.scalar(
        select(func.count()).select_from(queued.where(Conversation.is_urgent).subquery())
    )
    online = db.scalar(
        select(func.count())
        .select_from(Agent)
        .where(Agent.is_active, Agent.last_seen_at > utcnow() - ONLINE_WINDOW)
    )
    return LiveMetrics(
        queued=counts.get(ConversationStatus.QUEUED, 0),
        urgent_queued=urgent or 0,
        oldest_queued_at=oldest,
        in_bot=counts.get(ConversationStatus.BOT, 0),
        open=counts.get(ConversationStatus.OPEN, 0),
        pending=counts.get(ConversationStatus.PENDING, 0),
        agents_online=online or 0,
    )


def _require_cron(authorization: str | None) -> None:
    secret = get_settings().cron_secret
    if (
        not secret
        or not authorization
        or not hmac.compare_digest(authorization, f"Bearer {secret}")
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autorizado")


def mark_abandoned(db: Session) -> int:
    """Casos en cola sin respuesta humana tras `abandon_after_hours`. Idempotente: un caso solo
    se marca una vez por cada vez que entra en cola."""
    cutoff = utcnow() - timedelta(hours=get_settings().abandon_after_hours)
    event = aliased(ConversationEvent)
    already_marked = exists().where(
        event.conversation_id == Conversation.id,
        event.type == EventType.ABANDONED,
        event.created_at >= Conversation.queued_at,
    )
    candidates = db.scalars(
        select(Conversation)
        .where(
            Conversation.status == ConversationStatus.QUEUED,
            Conversation.queued_at < cutoff,
            ~already_marked,
        )
        .with_for_update(skip_locked=True)
    ).all()
    for conversation in candidates:
        events.record(
            db,
            conversation,
            EventType.ABANDONED,
            data={"hours": get_settings().abandon_after_hours},
        )
    db.commit()
    return len(candidates)


@router.api_route("/cron/daily-rollup", methods=["GET", "POST"], include_in_schema=False)
def daily_rollup(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> dict[str, int]:
    _require_cron(authorization)
    return {"abandoned_marked": mark_abandoned(db), "nps_sent": surveys.run_monthly_nps(db)}


@router.post("/dev/simulate-inbound", status_code=202)
def simulate_inbound(
    body: SimulateInboundIn,
    _: Agent = Depends(require_supervisor),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Inyecta un mensaje entrante con el mismo formato que Meta. Deshabilitado en producción."""
    if get_settings().is_production:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No encontrado")
    wamid = f"wamid.sim.{int(utcnow().timestamp() * 1000)}"
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [{"wa_id": body.wa_id, "profile": {"name": body.name}}],
                            "messages": [
                                {
                                    "from": body.wa_id,
                                    "id": wamid,
                                    "timestamp": str(int(utcnow().timestamp())),
                                    "type": "text",
                                    "text": {"body": body.text},
                                }
                            ],
                        },
                    }
                ]
            }
        ],
    }
    inbound.process_payload(db, payload)
    return {"status": "accepted", "wamid": wamid}
