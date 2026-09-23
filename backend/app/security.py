"""Demo auth: the role comes from headers set by the UI role switcher.

Production would put SSO/JWT here; the permission rules below stay the same:
an employee sees only their own profile, HR sees everything incl. aggregates and uploads.
"""

from typing import Literal

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel


class Viewer(BaseModel):
    role: Literal["employee", "hr"]
    employee_id: str | None = None


def get_viewer(x_role: str = Header(default="employee"), x_employee_id: str | None = Header(default=None)) -> Viewer:
    role = x_role.strip().lower()
    if role not in ("employee", "hr"):
        raise HTTPException(400, "X-Role must be 'employee' or 'hr'")
    return Viewer(role=role, employee_id=x_employee_id)


def require_hr(viewer: Viewer = Depends(get_viewer)) -> Viewer:
    if viewer.role != "hr":
        raise HTTPException(403, "Доступно только HR")
    return viewer


def ensure_can_view(viewer: Viewer, employee_id: str) -> None:
    if viewer.role != "hr" and viewer.employee_id != employee_id:
        raise HTTPException(403, "Сотрудник видит только свой профиль")
