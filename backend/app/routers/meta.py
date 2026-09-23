from fastapi import APIRouter

from app.config import settings
from app.models.api import Catalog, EmployeeBrief, Health
from app.models.dataset import GRADES
from app.state import store

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=Health)
def health():
    return Health(status="ok", as_of=store.as_of, employees=len(store.employees), events=len(store.events),
                  skills=len(store.skills), history=len(store.history), llm_enabled=settings.llm_enabled,
                  model=settings.openai_model if settings.llm_enabled else None)


@router.get("/catalog", response_model=Catalog)
def catalog():
    return Catalog(as_of=store.as_of, grades=GRADES, skills=list(store.skills.values()),
                   events=list(store.events.values()), role_profiles=list(store.role_profiles.values()))


@router.get("/employees", response_model=list[EmployeeBrief])
def employees(q: str = ""):
    """Directory for the login picker and HR search: names and positions only, no engagement data."""
    q = q.strip().lower()
    return [EmployeeBrief(employee_id=e.employee_id, full_name=e.full_name, role=e.role, grade=e.grade,
                          department=e.department, preferred_language=e.preferred_language)
            for e in store.employees.values()
            if not q or q in f"{e.employee_id} {e.full_name} {e.role} {e.department}".lower()]
