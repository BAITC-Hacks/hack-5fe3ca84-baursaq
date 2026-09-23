"""Dataset schema — mirrors data/career_quest/README.md one to one."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, field_validator

GRADES = ["Junior", "Middle", "Senior", "Lead"]
HistoryStatus = Literal["completed", "in_progress", "dropped", "no_show", "declined", "overdue"]


class Skill(BaseModel):
    skill_id: str
    name: str
    type: str = "hard"
    category: str = ""
    description: str = ""


class RoleProfile(BaseModel):
    role: str
    grade: str
    required_skills: dict[str, int] = {}
    critical_skills: list[str] = []


class CareerGoal(BaseModel):
    target_role: str
    target_grade: str


class Employee(BaseModel):
    employee_id: str
    full_name: str = ""
    department: str = ""
    role: str
    grade: str
    manager_id: str | None = None
    hire_date: dt.date | None = None
    tenure_months: int = 0
    work_format: str = "office"
    preferred_language: str = "ru"
    career_goal: CareerGoal | None = None
    skills: dict[str, int] = {}
    last_review_date: dt.date | None = None


class SkillGain(BaseModel):
    skill_id: str
    gain: int
    max_level: int = 5


class Event(BaseModel):
    event_id: str
    title: str
    description: str = ""
    type: str
    format: str
    duration_hours: float = 0
    mandatory: bool = False
    target_roles: list[str] = []
    target_grades: list[str] = []
    develops_skills: list[SkillGain] = []
    prerequisites: dict[str, int] = {}
    upcoming_sessions: list[dt.date] = []


class HistoryRecord(BaseModel):
    record_id: str
    employee_id: str
    event_id: str
    date: dt.date
    due_date: dt.date | None = None
    status: HistoryStatus
    completion_pct: int = 0
    score: int | None = None
    feedback_rating: int | None = None
    assigned_by: str = "self"

    @field_validator("due_date", "score", "feedback_rating", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        return None if v == "" else v
