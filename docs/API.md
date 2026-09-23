# Контракт v0.1 — frontend / backend / agent

Backend: http://127.0.0.1:8000. Vite proxy `/api` → backend. В production frontend обслуживает сам backend.
Интерактивная схема `/docs`, OpenAPI `/openapi.json`. Ошибка: `{"detail": "описание"}`; 401 требуется вход, 403 нет прав, 400 невалидный импорт/действие.

## HTTP
| Метод / путь | Тело | Ответ / права |
|---|---|---|
| GET /api/health | — | status, as_of_date, employee_count, agent_configured (наличие настроек, не проверка AI) |
| GET /api/demo/accounts | — | `[{employee_id, full_name}]` синтетические демо-аккаунты |
| POST /api/auth/login | `{role: "employee"\|"hr", employee_id?: string, password: string}` | `{token, role, employee_id}` |
| POST /api/auth/logout | — | Удаляет сессию |
| GET /api/employees | — | `[{employee_id, full_name, role, grade, department}]`; сотрудник видит только себя |
| GET /api/employees/{id} | — | Profile; сотрудник — только себя, HR — любого |
| GET /api/employees/{id}/candidates | — | Candidate[]; те же права |
| POST /api/employees/{id}/recommendations | `{language: "ru"\|"kk"\|"en"}` | RecommendationResult; те же права |
| POST /api/employees/{id}/complete | `{event_id: string}` | `{changed: boolean, profile: Profile}`; повтор идемпотентен |
| GET /api/hr/summary | — | HRSummary; только HR |
| POST /api/import | multipart: employees (JSON), history (CSV, опционально) | `{employees_imported, history_imported}`; только HR |

После входа: `Authorization: Bearer <token>`; токен хранить в sessionStorage и удалять при 401/выходе. Демо-пароли: employee-demo и hr-demo, можно переопределить через `.env`.

## Profile
```ts
{
  employee: {employee_id, full_name, role, grade, department, skills, career_goal, ...},
  effective_skills: Record<string, number>,
  skills: {skill_id: string, name: string, current: number, required: number, gap: number, critical: boolean}[],
  target: {role: string, grade: string, critical_skills: string[]},
  progress_pct: number,
  history: {record_id, event_id, date, status, completion_pct, title, ...}[],
  history_summary: Record<string, number>,
  as_of_date: string
}
```
`employee.skills` — исходная оценка, `effective_skills` — после ещё не учтённых завершений. UI использует skills/current и progress_pct, не пересчитывает сам.

## Candidate / рекомендация
```ts
{
  event_id: string, title: string, description: string, format: string, type: string,
  duration_hours: number, next_session: string | null, score: number,
  gaps: {skill_id: string, current: number, required: number, critical: boolean, gap_closed: number}[],
  history_risk_count: number,
  evidence: {factor: string, source: string, text: string}[],
  projection: {event_id: string, changes: {skill_id: string, name: string, before: number, after: number}[],
               progress_before: number, progress_after: number},
  reason?: string // обязателен у рекомендации, отсутствует у кандидата
}
```
score — внутренняя эвристика; не выводить как уверенность модели. Прогноз каждой карточки считается отдельно от текущего состояния, не суммировать их проценты.

## RecommendationResult и Python-интерфейс Umar
```python
async def recommend(engine, employee_id: str, language: str = 'ru') -> dict:
    ...
```
```ts
{
  mode: "rules" | "openai",
  warning: string | null,
  recommendations: (Candidate & {reason: string})[],
  empty_reason: string | null,
  trace: {tool: string, summary: string, duration_ms: number}[],
  duration_ms: number
}
```
Успешный AI-режим только после реального проверенного вызова. Можно добавить необязательные поля model/usage, не менять существующие.

Read-only методы агента:
- `engine.profile(employee_id)` → Profile.
- `engine.candidates(employee_id)` → Candidate[].
- `engine.simulate(employee_id, event_id)` → projection либо ValueError для недопустимого события.
- Не предоставлять LLM `engine.complete` / store / произвольный код / filesystem.

## HRSummary
```ts
{
  employee_count: number, as_of_date: string,
  skill_gaps: {skill_id: string, name: string, employee_count: number}[],
  no_next_step: {employee_id: string, full_name: string, reason: string}[],
  participation: {event_id: string, title: string, statuses: Record<string, number>}[]
}
```
Это доступность по правилам, не 200 AI-вызовов. Причину отсутствия шага показывать без выводов о мотивации человека.

## Импорт
employees: оригинальный `{meta, employees:[...]}`, массив профилей или один профиль. CSV — исходные столбцы датасета, UTF-8, запятые. Вся пачка проверяется до записи. Профили обновляются по employee_id, история — по record_id; неизвестные навыки, роли, события, дубли ID внутри пачки отклоняются. При замене профиля его локальные демо-завершения удаляются, чтобы не смешивать старый эксперимент с новой оценкой. Исходные JSON/CSV не меняются.
