// Mirror of backend/app/models/api.py — change both together (see AGENTS.md).

export type Lang = 'kk' | 'ru' | 'en'
export type Role = 'employee' | 'hr'

export interface Health {
  status: string
  as_of: string
  employees: number
  events: number
  skills: number
  history: number
  llm_enabled: boolean
  model: string | null
}

export interface Skill {
  skill_id: string
  name: string
  type: string
  category: string
  description: string
}

export interface SkillGain {
  skill_id: string
  gain: number
  max_level: number
}

export interface Event {
  event_id: string
  title: string
  description: string
  type: string
  format: string
  duration_hours: number
  mandatory: boolean
  target_roles: string[]
  target_grades: string[]
  develops_skills: SkillGain[]
  prerequisites: Record<string, number>
  upcoming_sessions: string[]
}

export interface RoleProfile {
  role: string
  grade: string
  required_skills: Record<string, number>
  critical_skills: string[]
}

export interface Catalog {
  as_of: string
  grades: string[]
  skills: Skill[]
  events: Event[]
  role_profiles: RoleProfile[]
}

export interface EmployeeBrief {
  employee_id: string
  full_name: string
  role: string
  grade: string
  department: string
  preferred_language: string
}

export interface Employee {
  employee_id: string
  full_name: string
  department: string
  role: string
  grade: string
  manager_id: string | null
  hire_date: string | null
  tenure_months: number
  work_format: string
  preferred_language: string
  career_goal: { target_role: string; target_grade: string } | null
  skills: Record<string, number>
  last_review_date: string | null
}

export interface SkillDelta {
  skill_id: string
  name: string
  before: number
  after: number
}

export interface SkillState {
  skill_id: string
  name: string
  type: string
  category: string
  assessed: number // level from the last review
  effective: number // assessed + gains of activities completed after last_review_date
  required_current: number
  required_target: number
  gap: number
  critical: boolean
  pending_from: string[] // event_ids that raised it after the last review
}

export interface Target {
  role: string
  grade: string
  source: 'career_goal' | 'next_grade' | 'current_grade'
  readiness_pct: number
  blockers: string[]
  total_gap: number
}

export interface TrajectoryStep {
  role: string
  grade: string
  status: 'passed' | 'current' | 'target' | 'future'
  readiness_pct: number
}

export interface HistoryItem {
  record_id: string
  event_id: string
  title: string
  type: string
  format: string
  mandatory: boolean
  date: string
  status: 'completed' | 'in_progress' | 'dropped' | 'no_show' | 'declined' | 'overdue'
  completion_pct: number
  score: number | null
  feedback_rating: number | null
  assigned_by: string
}

export interface NextStep {
  event_id: string
  title: string
  type: string
  format: string
  duration_hours: number
  next_session: string | null
  gains: SkillDelta[]
  closes_gap: boolean
  in_progress: boolean
}

export interface EmployeeProfile {
  employee: Employee
  manager_name: string | null
  skills: SkillState[]
  target: Target
  trajectory: TrajectoryStep[]
  history: HistoryItem[]
  history_stats: Record<string, number>
  next_steps: NextStep[]
}

export type FactorKind =
  | 'skill_gap'
  | 'critical_skill'
  | 'grade_requirement'
  | 'growth'
  | 'career_goal'
  | 'history'
  | 'motivation'
  | 'schedule'
  | 'work_format'
  | 'prerequisites'
  | 'effort'

export interface Factor {
  kind: FactorKind
  label: string
  impact: number // signed contribution to the score
}

export interface Recommendation {
  rank: number
  event_id: string
  title: string
  type: string
  format: string
  duration_hours: number
  next_session: string | null
  score: number
  rationale: string
  factors: Factor[]
  gains: SkillDelta[]
  readiness_after_pct: number
}

export interface Rejected {
  event_id: string | null
  skill_id: string | null
  title: string
  reason: string
}

export interface TraceStep {
  step: string
  detail: string
  ms: number
}

export interface RecommendationResponse {
  employee_id: string
  language: Lang
  source: 'llm' | 'fallback'
  model: string | null
  latency_ms: number
  summary: string
  readiness_now_pct: number
  recommendations: Recommendation[]
  rejected: Rejected[]
  trace: TraceStep[]
}

export interface HistoryRecord {
  record_id: string
  employee_id: string
  event_id: string
  date: string
  status: string
  completion_pct: number
  score: number | null
  feedback_rating: number | null
  assigned_by: string
}

// POST /employees/{id}/feedback {event_id} — «Не сейчас»: hides the step, history is not touched
export interface FeedbackResponse {
  status: 'snoozed'
  event_id: string
}

export interface CompleteResponse {
  record: HistoryRecord
  changes: SkillDelta[]
  readiness_before: number
  readiness_after: number
  profile: EmployeeProfile
}

export interface LaggingSkill {
  skill_id: string
  name: string
  category: string
  below_current: number
  below_target: number
  critical_blockers: number
  avg_gap: number
}

export interface NoStepEmployee {
  employee_id: string
  full_name: string
  role: string
  grade: string
  reason: string
}

export interface EventParticipation {
  event_id: string
  title: string
  type: string
  format: string
  mandatory: boolean
  total: number
  completed: number
  in_progress: number
  dropped: number
  no_show: number
  declined: number
  overdue: number
  completion_rate: number
  avg_feedback: number | null
}

export interface AtRiskEmployee {
  employee_id: string
  full_name: string
  role: string
  grade: string
  signals: string[]
  last_voluntary_date: string | null
}

export interface HROverview {
  as_of: string
  totals: Record<string, number>
  lagging_skills: LaggingSkill[]
  no_recommendation: NoStepEmployee[]
  participation: EventParticipation[]
  at_risk: AtRiskEmployee[]
}

export interface UploadResult {
  added: Record<string, number>
  updated: Record<string, number>
  employee_ids: string[]
  warnings: string[]
}
