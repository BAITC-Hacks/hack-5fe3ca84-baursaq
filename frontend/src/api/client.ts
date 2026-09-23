import type { CompleteResponse as ApiComplete, EmployeeProfile as ApiProfile, FeedbackResponse, HROverview as ApiHr, Lang, RecommendationResponse as ApiRecommendations, Role, UploadResult } from './types'
import type { CompleteResponse, EmployeeProfile, EmployeeSummary, HrOverview, RecommendationResponse } from './view'

export type ApiContext = { role: Role; employeeId: string; language: Lang }

async function request<T>(path: string, context: ApiContext, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('X-Role', context.role)
  headers.set('X-Employee-Id', context.employeeId)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  let response: Response
  try { response = await fetch(`/api${path}`, { ...init, headers }) }
  catch { throw new Error('Нет связи с сервером. Проверьте, что API запущен.') }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(typeof body?.detail === 'string' ? body.detail : `Сервер вернул ошибку ${response.status}`)
  }
  return response.json() as Promise<T>
}

function profileView(source: ApiProfile): EmployeeProfile {
  return {
    ...source.employee,
    readiness_pct: source.target.readiness_pct,
    target_role: source.target.role,
    target_grade: source.target.grade,
    skills: source.skills.map(skill => ({ skill_id: skill.skill_id, name: skill.name, assessed_level: skill.assessed, effective_level: skill.effective, required_level: skill.required_target, critical: skill.critical })),
    history: source.history,
    available_steps: source.next_steps.map(step => ({ ...step, upcoming_sessions: step.next_session ? [step.next_session] : [] })),
  }
}

function recommendationsView(source: ApiRecommendations): RecommendationResponse {
  return {
    source: source.source,
    model: source.model,
    latency_ms: source.latency_ms,
    summary: source.summary,
    recommendations: source.recommendations.map(item => ({ ...item, gains: item.gains.map(gain => ({ ...gain, skill_name: gain.name })), upcoming_sessions: item.next_session ? [item.next_session] : [] })),
    rejected: source.rejected,
    trace: source.trace,
  }
}

function hrView(source: ApiHr): HrOverview {
  return {
    lagging_skills: source.lagging_skills.map(item => ({ ...item, count: item.below_target })),
    participation: source.participation,
    no_next_step: source.no_recommendation,
    disengaged: source.at_risk.map(item => ({ ...item, reason: item.signals.join('; ') })),
  }
}

export const api = {
  employees: async (context: ApiContext, q = ''): Promise<EmployeeSummary[]> => request<EmployeeSummary[]>(`/employees?q=${encodeURIComponent(q)}`, context),
  employee: async (id: string, context: ApiContext): Promise<EmployeeProfile> => profileView(await request<ApiProfile>(`/employees/${encodeURIComponent(id)}?lang=${context.language}`, context)),
  recommend: async (id: string, context: ApiContext): Promise<RecommendationResponse> => recommendationsView(await request<ApiRecommendations>(`/employees/${encodeURIComponent(id)}/recommendations`, context, { method: 'POST', body: JSON.stringify({ language: context.language }) })),
  complete: async (id: string, eventId: string, context: ApiContext): Promise<CompleteResponse> => {
    const source = await request<ApiComplete>(`/employees/${encodeURIComponent(id)}/complete`, context, { method: 'POST', body: JSON.stringify({ event_id: eventId }) })
    return { readiness_before_pct: source.readiness_before, readiness_after_pct: source.readiness_after, profile: profileView(source.profile) }
  },
  feedback: (id: string, eventId: string, context: ApiContext) => request<FeedbackResponse>(`/employees/${encodeURIComponent(id)}/feedback`, context, { method: 'POST', body: JSON.stringify({ event_id: eventId }) }),
  hr: async (context: ApiContext): Promise<HrOverview> => hrView(await request<ApiHr>('/hr/overview', context)),
  upload: (files: File[], context: ApiContext): Promise<UploadResult> => {
    const form = new FormData()
    files.forEach(file => form.append('files', file))
    return request<UploadResult>('/dataset/upload', context, { method: 'POST', body: form })
  },
  reset: (context: ApiContext) => request<{ status: string }>('/dataset/reset', context, { method: 'POST' }),
}
