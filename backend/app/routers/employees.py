from fastapi import APIRouter, Depends, HTTPException

from app.agents import recommender
from app.models.api import (
    CompleteRequest,
    CompleteResponse,
    EmployeeProfile,
    RecommendationResponse,
    RecommendRequest,
)
from app.security import Viewer, ensure_can_view, get_viewer
from app.services import engine
from app.state import store

router = APIRouter(prefix="/api/employees", tags=["employee"])


def _check(emp_id: str, viewer: Viewer) -> None:
    ensure_can_view(viewer, emp_id)
    if emp_id not in store.employees:
        raise HTTPException(404, f"Сотрудник {emp_id} не найден")


@router.get("/{emp_id}", response_model=EmployeeProfile)
def profile(emp_id: str, lang: str | None = None, viewer: Viewer = Depends(get_viewer)):
    _check(emp_id, viewer)
    return engine.build_profile(store, emp_id, lang)


@router.post("/{emp_id}/recommendations", response_model=RecommendationResponse)
async def recommendations(emp_id: str, body: RecommendRequest | None = None, viewer: Viewer = Depends(get_viewer)):
    _check(emp_id, viewer)
    return await recommender.recommend(store, emp_id, body.language if body else None)


@router.post("/{emp_id}/complete", response_model=CompleteResponse)
def complete(emp_id: str, body: CompleteRequest, viewer: Viewer = Depends(get_viewer)):
    _check(emp_id, viewer)
    if body.event_id not in store.events:
        raise HTTPException(404, f"Мероприятие {body.event_id} не найдено")
    try:
        return engine.complete(store, emp_id, body.event_id, body.score, body.feedback_rating)
    except ValueError:
        raise HTTPException(409, "Мероприятие уже пройдено") from None
