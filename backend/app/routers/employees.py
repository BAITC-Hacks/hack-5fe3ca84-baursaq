from fastapi import APIRouter, Depends, HTTPException

from app.agents import recommender
from app.models.api import (
    CompleteRequest,
    CompleteResponse,
    EmployeeProfile,
    FeedbackRequest,
    FeedbackResponse,
    RecommendationResponse,
    RecommendRequest,
)
from app.security import Viewer, ensure_can_view, get_viewer
from app.services import engine
from app.state import store

router = APIRouter(prefix="/api/employees", tags=["employee"])

NOT_ALLOWED = {
    "completed": "Мероприятие уже пройдено",
    "mandatory": "Обязательное обучение отмечается в HR-системе, а не здесь",
    "audience": "Мероприятие не предназначено для роли и грейда сотрудника",
    "no_sessions": "У мероприятия нет ближайших сессий",
    "prereq": "Не выполнены пререквизиты мероприятия",
}


def _check(emp_id: str, viewer: Viewer) -> None:
    ensure_can_view(viewer, emp_id)
    if emp_id not in store.employees:
        raise HTTPException(404, f"Сотрудник {emp_id} не найден")


def _check_event(event_id: str) -> None:
    if event_id not in store.events:
        raise HTTPException(404, f"Мероприятие {event_id} не найдено")


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
    _check_event(body.event_id)
    try:
        return engine.complete(store, emp_id, body.event_id, body.score, body.feedback_rating)
    except ValueError as e:
        raise HTTPException(409, NOT_ALLOWED.get(str(e).split(":")[0], "Мероприятие сейчас недоступно")) from None


@router.post("/{emp_id}/feedback", response_model=FeedbackResponse)
def feedback(emp_id: str, body: FeedbackRequest, viewer: Viewer = Depends(get_viewer)):
    """«Не сейчас»: the step disappears from recommendations; nothing is written to the participation history."""
    _check(emp_id, viewer)
    _check_event(body.event_id)
    store.snooze(emp_id, body.event_id)
    return FeedbackResponse(status="snoozed", event_id=body.event_id)
