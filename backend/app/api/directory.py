from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models import Agent
from app.schemas.directory import DirectoryOut, ImportPreview, WpExport
from app.services import directory as svc

router = APIRouter(prefix="/directory", tags=["directory"])


@router.get("", response_model=DirectoryOut)
def list_directory(
    _: Agent = Depends(require_permission(Permission.DIRECTORY_VIEW)),
    db: Session = Depends(get_db),
):
    """Todo el directorio de una vez (unos cientos de fichas): la búsqueda es instantánea en la
    tableta, sin pedir nada al servidor por cada letra que se escribe."""
    return svc.listing(db)


@router.post("/import", response_model=ImportPreview)
def import_directory(
    body: WpExport,
    apply: bool = False,
    agent: Agent = Depends(require_permission(Permission.DIRECTORY_MANAGE)),
    db: Session = Depends(get_db),
):
    """Sin `apply`, solo muestra qué cambiaría. Con `apply=true`, lo guarda."""
    return svc.run(db, agent, body, apply=apply)
