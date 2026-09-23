"""API contract. Source of truth for frontend/src/api/types.ts — change both together."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel

from app.models.dataset import Employee, Event, HistoryRecord, RoleProfile, Skill

Lang = Literal["kk", "ru", "en"]


class Health(BaseModel):
    status: str
    as_of: dt.date
    employees: int
    events: int
    skills: int
    history: int
    llm_enabled: bool
    model: str | None


class Catalog(BaseModel):
    as_of: dt.date
    grades: list[str]
    skills: list[Skill]
    events: list[Event]
    role_profiles: list[RoleProfile]


class EmployeeBrief(BaseModel):
    employee_id: str
    full_name: str
    role: str
    grade: str
    department: str
    preferred_language: str


class SkillDelta(BaseModel):
    skill_id: str
    name: str
    before: int
    after: int


class SkillState(BaseModel):
    skill_id: str
    name: str
    type: str
    category: str
    assessed: int  # level from the last review
    effective: int  # assessed + gains of activities completed after last_review_date
    required_current: int  # requirement of the current role/grade (0 = not required)
    required_target: int  # requirement of the target role/grade (0 = not required)
    gap: int  # max(0, required_target - effective)
    critical: bool  # critical skill of the target grade
    pending_from: list[str] = []  # event_ids completed after the last review that raised this skill


class Target(BaseModel):
    role: str
    grade: str
    source: Literal["career_goal", "next_grade", "current_grade"]
    readiness_pct: int
    blockers: list[str]  # critical skills still below the target requirement
    total_gap: int


class TrajectoryStep(BaseModel):
    role: str
    grade: str
    status: Literal["passed", "current", "target", "future"]
    readiness_pct: int


class HistoryItem(BaseModel):
    record_id: str
    event_id: str
    title: str
    type: str
    format: str
    mandatory: bool
    date: dt.date
    status: str
    completion_pct: int
    score: int | None
    feedback_rating: int | None
    assigned_by: str


class NextStep(BaseModel):
    event_id: str
    title: str
    type: str
    format: str
    duration_hours: float
    next_session: dt.date | None
    gains: list[SkillDelta]
    closes_gap: bool
    in_progress: bool


class EmployeeProfile(BaseModel):
    employee: Employee
    manager_name: str | None
    skills: list[SkillState]
    target: Target
    trajectory: list[TrajectoryStep]
    history: list[HistoryItem]
    history_stats: dict[str, int]
    next_steps: list[NextStep]


FactorKind = Literal[
    "skill_gap",
    "critical_skill",
    "grade_requirement",
    "growth",
    "career_goal",
    "history",
    "motivation",
    "schedule",
    "work_format",
    "prerequisites",
    "effort",
]


class Factor(BaseModel):
    kind: FactorKind
    label: str  # short chip text
    impact: float  # signed contribution to the score


class Recommendation(BaseModel):
    rank: int
    event_id: str
    title: str
    type: str
    format: str
    duration_hours: float
    next_session: dt.date | None
    score: float
    rationale: str
    factors: list[Factor]
    gains: list[SkillDelta]
    readiness_after_pct: int


class Rejected(BaseModel):
    event_id: str | None = None
    skill_id: str | None = None
    title: str
    reason: str


class TraceStep(BaseModel):
    step: str
    detail: str
    ms: int = 0


class RecommendationResponse(BaseModel):
    employee_id: str
    language: Lang
    source: Literal["llm", "fallback"]
    model: str | None
    latency_ms: int
    summary: str
    readiness_now_pct: int
    recommendations: list[Recommendation]
    rejected: list[Rejected]
    trace: list[TraceStep]


class RecommendRequest(BaseModel):
    language: Lang | None = None  # default: employee.preferred_language


class CompleteRequest(BaseModel):
    event_id: str
    score: int | None = None
    feedback_rating: int | None = None


class CompleteResponse(BaseModel):
    record: HistoryRecord
    changes: list[SkillDelta]
    readiness_before: int
    readiness_after: int
    profile: EmployeeProfile


class LaggingSkill(BaseModel):
    skill_id: str
    name: str
    category: str
    below_current: int  # employees below the requirement of their CURRENT grade
    below_target: int  # employees below the requirement of their TARGET grade
    critical_blockers: int  # ...of which the skill is critical for the target
    avg_gap: float


class NoStepEmployee(BaseModel):
    employee_id: str
    full_name: str
    role: str
    grade: str
    reason: str


class EventParticipation(BaseModel):
    event_id: str
    title: str
    type: str
    format: str
    mandatory: bool
    total: int
    completed: int
    in_progress: int
    dropped: int
    no_show: int
    declined: int
    overdue: int
    completion_rate: float
    avg_feedback: float | None


class AtRiskEmployee(BaseModel):
    employee_id: str
    full_name: str
    role: str
    grade: str
    signals: list[str]
    last_voluntary_date: dt.date | None


class HROverview(BaseModel):
    as_of: dt.date
    totals: dict[str, int]
    lagging_skills: list[LaggingSkill]
    no_recommendation: list[NoStepEmployee]
    participation: list[EventParticipation]
    at_risk: list[AtRiskEmployee]


class UploadResult(BaseModel):
    added: dict[str, int]
    updated: dict[str, int]
    employee_ids: list[str]
    warnings: list[str]
