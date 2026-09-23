from fastapi import APIRouter, Depends

from app.models.api import HROverview
from app.security import require_hr
from app.services import hr
from app.state import store

router = APIRouter(prefix="/api/hr", tags=["hr"], dependencies=[Depends(require_hr)])


@router.get("/overview", response_model=HROverview)
def overview():
    return hr.overview(store)
