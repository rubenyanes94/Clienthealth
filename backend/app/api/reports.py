from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.base import utcnow
from app.db.session import get_db
from app.models import Agent
from app.services import report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])

MAX_DAYS = 366


@router.get(
    "/indicators.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def indicators_pdf(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    area_id: int | None = None,
    agent: Agent = Depends(require_permission(Permission.METRICS_VIEW)),
    db: Session = Depends(get_db),
) -> Response:
    """Informe en PDF con los indicadores del período, conclusiones y gráficas."""
    if date_to < date_from:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "«to» es anterior a «from»")
    if date_to - date_from > timedelta(days=MAX_DAYS):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "El período máximo es un año")
    data = report_pdf.collect(db, date_from, date_to, area_id, agent.name, utcnow())
    filename = f"informe-atencion_{date_from}_{date_to}.pdf"
    return Response(
        content=report_pdf.build(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
