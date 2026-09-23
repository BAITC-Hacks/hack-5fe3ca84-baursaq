from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CareerGoal(BaseModel):
    target_role: str
    target_grade: Literal['Junior', 'Middle', 'Senior', 'Lead']


class Employee(BaseModel):
    employee_id: str = Field(min_length=1, max_length=100)
    full_name: str = Field(min_length=1, max_length=200)
    department: str = ''
    role: str
    grade: Literal['Junior', 'Middle', 'Senior', 'Lead']
    manager_id: str | None = None
    hire_date: date | None = None
    tenure_months: int = Field(default=0, ge=0)
    work_format: Literal['office', 'hybrid', 'remote'] = 'hybrid'
    preferred_language: Literal['kk', 'ru', 'en'] = 'ru'
    career_goal: CareerGoal | None = None
    skills: dict[str, int]
    last_review_date: date

    @field_validator('skills')
    @classmethod
    def valid_skills(cls, value):
        if any(isinstance(v, bool) or not 0 <= v <= 5 for v in value.values()):
            raise ValueError('Уровни навыков должны быть от 0 до 5')
        return value


class HistoryRecord(BaseModel):
    record_id: str = Field(min_length=1, max_length=150)
    employee_id: str
    event_id: str
    date: date
    due_date: date | None = None
    status: Literal['completed', 'in_progress', 'dropped', 'no_show', 'declined', 'overdue']
    completion_pct: int = Field(ge=0, le=100)
    score: int | None = Field(default=None, ge=0, le=100)
    feedback_rating: int | None = Field(default=None, ge=1, le=5)
    assigned_by: Literal['self', 'manager', 'hr'] = 'self'


class LoginRequest(BaseModel):
    role: Literal['employee', 'hr']
    employee_id: str | None = None
    password: str


class CompleteRequest(BaseModel):
    event_id: str


class RecommendationRequest(BaseModel):
    language: Literal['ru', 'kk', 'en'] = 'ru'
