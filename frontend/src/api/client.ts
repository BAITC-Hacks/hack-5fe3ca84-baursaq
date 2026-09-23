import type {
  Catalog,
  CompleteResponse,
  EmployeeBrief,
  EmployeeProfile,
  Health,
  HROverview,
  Lang,
  RecommendationResponse,
  Role,
  UploadResult,
} from './types'

// Demo auth: the role switcher in the header calls setSession(); every request carries it.
let session: { role: Role; employeeId?: string } = { role: 'hr' }

export function setSession(role: Role, employeeId?: string) {
  session = { role, employeeId }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('X-Role', session.role)
  if (session.employeeId) headers.set('X-Employee-Id', session.employeeId)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const res = await fetch(`/api${path}`, { ...init, headers })
  if (!res.ok) {
    const detail = await res.json().then((j) => j.detail).catch(() => res.statusText)
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => request<Health>('/health'),
  catalog: () => request<Catalog>('/catalog'),
  employees: (q = '') => request<EmployeeBrief[]>(`/employees?q=${encodeURIComponent(q)}`),
  profile: (id: string, lang?: Lang) => request<EmployeeProfile>(`/employees/${id}${lang ? `?lang=${lang}` : ''}`),
  recommend: (id: string, language?: Lang) =>
    request<RecommendationResponse>(`/employees/${id}/recommendations`, {
      method: 'POST',
      body: JSON.stringify({ language: language ?? null }),
    }),
  complete: (id: string, event_id: string) =>
    request<CompleteResponse>(`/employees/${id}/complete`, { method: 'POST', body: JSON.stringify({ event_id }) }),
  hrOverview: () => request<HROverview>('/hr/overview'),
  upload: (files: File[]) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return request<UploadResult>('/dataset/upload', { method: 'POST', body: form })
  },
  reset: () => request<{ status: string }>('/dataset/reset', { method: 'POST' }),
}
