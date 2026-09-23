export type Role = 'employee' | 'hr'
export type Language = 'kk' | 'ru' | 'en'

export interface EmployeeSummary {
  employee_id: string
  full_name: string
  role?: string
  grade?: string
  department?: string
}

export interface Skill {
  skill_id: string
  name: string
  assessed_level: number
  effective_level: number
  required_level: number
  critical: boolean
}

export interface HistoryItem {
  event_id: string
  title?: string
  date?: string
  status: string
  format?: string
}

export interface EventItem {
  event_id: string
  title: string
  description?: string
  type?: string
  format?: string
  duration_hours?: number
  upcoming_sessions?: string[]
}

export interface EmployeeProfile extends EmployeeSummary {
  tenure_months?: number
  work_format?: string
  preferred_language?: string
  career_goal?: { target_role: string; target_grade: string } | null
  target_role?: string
  target_grade?: string
  readiness_pct?: number
  skills?: Skill[] | Record<string, number>
  trajectory?: string[]
  history?: HistoryItem[]
  available_steps?: EventItem[]
  available_events?: EventItem[]
}

export interface Factor {
  label?: string
  detail?: string
  name?: string
  value?: string | number
}

export interface Recommendation {
  event_id: string
  title?: string
  event?: EventItem
  rationale?: string
  factors?: Array<Factor | string>
  gains?: Array<{ skill_id?: string; skill_name?: string; before?: number; after?: number; from?: number; to?: number }>
  readiness_after_pct?: number
  format?: string
  upcoming_sessions?: string[]
}

export interface RecommendationResponse {
  recommendations?: Recommendation[]
  rejected?: Array<{ event_id?: string | null; title?: string; reason?: string; rationale?: string }> | string
  why_not?: string
  trace?: Array<string | { step?: string; tool?: string; message?: string; detail?: string }>
}

export interface CompleteResponse {
  readiness_before_pct?: number
  readiness_after_pct?: number
  before_pct?: number
  after_pct?: number
  profile?: EmployeeProfile
}

export interface HrOverview {
  lagging_skills?: Array<{ skill_id?: string; name?: string; skill_name?: string; count?: number; employee_count?: number }>
  skill_gaps?: Array<{ skill_id?: string; name?: string; skill_name?: string; count?: number; employee_count?: number }>
  participation?: Array<{ event_id?: string; title?: string; event_title?: string; completed?: number; no_show?: number; declined?: number; count?: number }>
  no_next_step?: Array<{ employee_id?: string; full_name?: string; reason?: string }>
  without_recommendations?: Array<{ employee_id?: string; full_name?: string; reason?: string }>
  disengaged?: Array<{ employee_id?: string; full_name?: string; reason?: string; count?: number }>
}
