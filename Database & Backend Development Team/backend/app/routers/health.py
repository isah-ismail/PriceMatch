from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import __version__
from ..database import get_db
from ..errors import ServiceUnavailableError
from ..schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Liveness + database check")
def health(db: Session = Depends(get_db)) -> HealthOut:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - we want any DB failure to surface as 503
        raise ServiceUnavailableError("Database is not reachable", details=str(exc.__class__.__name__)) from exc
    return HealthOut(status="ok", database="ok", version=__version__)
