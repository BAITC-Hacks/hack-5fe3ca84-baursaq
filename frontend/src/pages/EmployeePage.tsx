import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, CalendarDays, Check, CheckCircle2, Clock3, Compass, RotateCcw, Sparkles, Target, XCircle } from 'lucide-react'
import RecommendationDetails from '../components/RecommendationDetails'
import { api, type ApiContext } from '../api/client'
import type { EmployeeProfile, EventItem, Recommendation, RecommendationResponse, Skill } from '../api/view'

const grades = ['Junior', 'Middle', 'Senior', 'Lead']
const statuses: Record<string, string> = { completed: 'Пройдено', no_show: 'Не пришёл', declined: 'Отказ', dropped: 'Прервано', in_progress: 'В процессе', overdue: 'Просрочено' }
const formats: Record<string, string> = { self_paced: 'В своём темпе', online: 'Онлайн', offline: 'Офлайн' }
const pct = (value?: number) => Math.max(0, Math.min(100, Math.round(value ?? 0)))
const name = (value?: string) => value?.replace(/^SK_/, '').replaceAll('_', ' ') ?? 'Навык'

function skillsOf(profile: EmployeeProfile): Skill[] {
  if (Array.isArray(profile.skills)) return profile.skills
  return Object.entries(profile.skills ?? {}).map(([skill_id, level]) => ({ skill_id, name: name(skill_id), assessed_level: level, effective_level: level, required_level: level, critical: false }))
}

export default function EmployeePage({ context }: { context: ApiContext }) {
  const [profile, setProfile] = useState<EmployeeProfile | null>(null)
  const [result, setResult] = useState<RecommendationResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [recommending, setRecommending] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')

  const load = async () => {
    setLoading(true); setError(''); setResult(null)
    try { setProfile(await api.employee(context.employeeId, context)) }
    catch (cause) { setError((cause as Error).message) }
    finally { setLoading(false) }
  }
  useEffect(() => {
    let active = true
    api.employee(context.employeeId, context)
      .then(data => { if (active) setProfile(data) })
      .catch(cause => { if (active) setError((cause as Error).message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [context])
  useEffect(() => { if (!toast) return; const timer = window.setTimeout(() => setToast(''), 4500); return () => clearTimeout(timer) }, [toast])

  const recommend = async () => {
    setRecommending(true); setError(''); setResult(null)
    try { setResult(await api.recommend(context.employeeId, context)) }
    catch (cause) { setError((cause as Error).message) }
    finally { setRecommending(false) }
  }
  const complete = async (eventId: string) => {
    setBusy(eventId); setError('')
    try {
      const response = await api.complete(context.employeeId, eventId, context)
      const before = response.readiness_before_pct ?? response.before_pct ?? profile?.readiness_pct
      const next = response.profile ?? await api.employee(context.employeeId, context)
      setProfile(next)
      const after = response.readiness_after_pct ?? response.after_pct ?? next.readiness_pct
      setToast(before != null && after != null ? `Шаг пройден. Готовность: ${pct(before)}% → ${pct(after)}%` : 'Шаг отмечен пройденным. Прогресс обновлён.')
      setResult(null)
      setRecommending(true)
      setResult(await api.recommend(context.employeeId, context))
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(null); setRecommending(false) }
  }
  const decline = async (eventId: string) => {
    setBusy(eventId); setError('')
    try { await api.feedback(context.employeeId, eventId, context); setToast('Шаг скрыт — история участия не изменена'); setResult(null); setRecommending(true); setResult(await api.recommend(context.employeeId, context)) }
    catch (cause) { setError((cause as Error).message) }
    finally { setBusy(null); setRecommending(false) }
  }

  const skills = useMemo(() => profile ? skillsOf(profile).filter(skill => skill.required_level > 0 || skill.critical).sort((a, b) => Number(b.critical) - Number(a.critical) || (b.required_level - b.effective_level) - (a.required_level - a.effective_level)) : [], [profile])
  if (loading && !profile) return <div className="loading-panel"><div className="spinner" /> Загружаем профиль сотрудника…</div>
  if (!profile) return <div className="empty-state"><XCircle size={34} /><h2>Не удалось открыть профиль</h2><p>{error}</p><button className="button primary" onClick={load}>Повторить</button></div>
  const targetGrade = profile.career_goal?.target_grade ?? profile.target_grade ?? grades[Math.min(grades.indexOf(profile.grade ?? 'Junior') + 1, 3)]
  const targetRole = profile.career_goal?.target_role ?? profile.target_role ?? profile.role
  const history = profile.history ?? []
  const events = profile.available_steps ?? profile.available_events ?? []
  const recs = result?.recommendations ?? []

  return <>
    <div className="page-heading"><div><span className="eyebrow">ПРОСТРАНСТВО СОТРУДНИКА</span><h1>Ваш путь развития</h1><p>Понятные шаги к следующей карьерной цели.</p></div><span className="today-badge"><CalendarDays size={16} /> Данные на 1 октября 2026</span></div>
    {error && <div className="alert" role="alert">{error}<button onClick={() => setError('')}>Закрыть</button></div>}
    {toast && <div className="toast" role="status"><CheckCircle2 size={18} />{toast}</div>}
    <div className="employee-layout"><div className="main-column">
      <section className="card hero-card"><div className="hero-top"><div className="avatar">{profile.full_name.split(' ').map(part => part[0]).slice(0, 2).join('')}</div><div><div className="muted small">ПРОФИЛЬ СОТРУДНИКА · {profile.employee_id}</div><h2>{profile.full_name}</h2><p>{profile.role} · {profile.grade}</p></div></div><div className="hero-meta"><span>{profile.department}</span><span>{profile.tenure_months != null ? `${profile.tenure_months} мес. в компании` : 'Стаж не указан'}</span><span>{profile.work_format === 'remote' ? 'Удалённо' : profile.work_format === 'hybrid' ? 'Гибридно' : 'В офисе'}</span></div></section>
      <section className="card trajectory-card"><div className="section-title"><div><span className="icon-chip"><Target size={19} /></span><h2>Карьерная траектория</h2></div><span className="goal-tag">Цель: {targetRole} · {targetGrade}</span></div><div className="trajectory-line">{grades.map((grade, index) => <div key={grade} className={`grade-node ${grade === profile.grade ? 'current' : ''} ${grades.indexOf(profile.grade ?? '') > index ? 'passed' : ''} ${grade === targetGrade ? 'target' : ''}`}><div className="node-dot">{grades.indexOf(profile.grade ?? '') > index ? <Check size={15} /> : index + 1}</div><strong>{grade}</strong><span>{grade === profile.grade ? 'Сейчас' : grade === targetGrade ? 'Цель' : ''}</span></div>)}</div><div className="readiness-row"><div><strong>Готовность к цели</strong><p>Доля выполненных требований целевого грейда</p></div><strong className="readiness-value">{pct(profile.readiness_pct)}%</strong></div><div className="progress-track large"><div style={{ width: `${pct(profile.readiness_pct)}%` }} /></div></section>
      <section className="card"><div className="section-title"><div><span className="icon-chip"><Compass size={19} /></span><h2>Навыки для следующего шага</h2></div><span className="muted small">Уровни от 0 до 5</span></div>{skills.length ? <div className="skill-list">{skills.map(skill => <div className="skill-row" key={skill.skill_id}><div className="skill-label"><strong>{name(skill.name)}</strong>{skill.critical && <span className="critical-tag">Ключевой</span>}{skill.effective_level > skill.assessed_level && <span className="gain-tag">+{skill.effective_level - skill.assessed_level} после оценки</span>}</div><div className="skill-values">{skill.effective_level} / {skill.required_level}</div><div className="skill-track"><div className="required-marker" style={{ left: `${Math.min(skill.required_level, 5) * 20}%` }} /><div className={skill.effective_level >= skill.required_level ? 'met' : ''} style={{ width: `${Math.min(skill.effective_level, 5) * 20}%` }} /></div></div>)}</div> : <p className="muted">Данные о навыках пока недоступны.</p>}<div className="legend"><span><i className="legend-fill" /> Эффективный уровень</span><span><i className="legend-line" /> Требуется для цели</span></div></section>
      <section className="card"><div className="section-title"><div><span className="icon-chip"><Clock3 size={19} /></span><h2>История участия</h2></div><span className="muted small">{history.length} записей</span></div>{history.length ? <div className="history-list">{history.slice().sort((a, b) => (b.date ?? "").localeCompare(a.date ?? "")).slice(0, 8).map((item, index) => <div key={`${item.event_id}-${index}`} className="history-item"><span className={`history-dot ${item.status}`} /><div><strong>{item.title ?? item.event_id}</strong><span>{item.date ?? 'Дата не указана'}</span></div><span className={`status ${item.status}`}>{statuses[item.status] ?? item.status}</span></div>)}</div> : <p className="muted">История участия появится после первой активности.</p>}</section>
    </div><div className="side-column">
      <section className="card recommendation-panel"><div className="recommendation-head"><div className="sparkle-icon"><Sparkles size={23} /></div><span className="eyebrow">AI-НАВИГАТОР</span><h2>Куда двигаться дальше?</h2><p>Учитываем цель, разрывы навыков, пройденные шаги и формат работы.</p><button className="button primary wide" onClick={recommend} disabled={recommending || !!busy}>{recommending ? 'Подбираем шаги…' : result ? 'Обновить рекомендации' : 'Подобрать шаги'}<ArrowRight size={17} /></button></div>
        {recommending && <div className="agent-waiting" role="status"><div className="mini-spinner" aria-hidden="true" />Агент анализирует профиль…</div>}
        {result && !recommending && <RecommendationDetails result={result}>
          {recs.length ? recs.map((rec, index) => <RecommendationCard key={`${rec.event_id}-${index}`} rec={rec} index={index} busy={busy} onComplete={complete} onDecline={decline} />) : <div className="empty-mini"><CheckCircle2 size={24} /><strong>Подходящих шагов сейчас нет</strong><p>Проверьте цель или доступные мероприятия позже.</p></div>}
        </RecommendationDetails>}
      </section>
      <section className="card steps-card"><div className="section-title"><div><span className="icon-chip"><RotateCcw size={19} /></span><h2>Доступные шаги</h2></div></div>{events.length ? events.slice(0, 6).map(event => <div className="available-item" key={event.event_id}><strong>{event.title}</strong><span>{formats[event.format ?? ''] ?? event.format ?? 'Активность'}{event.duration_hours ? ` · ${event.duration_hours} ч` : ''}</span></div>) : <p className="muted">Нажмите «Подобрать шаги», чтобы увидеть персональный план.</p>}</section>
    </div></div>
  </>
}

function RecommendationCard({ rec, index, busy, onComplete, onDecline }: { rec: Recommendation; index: number; busy: string | null; onComplete: (id: string) => void; onDecline: (id: string) => void }) {
  const event: EventItem | undefined = rec.event
  const session = (rec.upcoming_sessions ?? event?.upcoming_sessions)?.[0]
  return <div className="rec-card"><div className="rec-top"><span className="rec-number">ШАГ {index + 1}</span><span className="format-tag">{formats[rec.format ?? event?.format ?? ''] ?? rec.format ?? event?.format ?? 'Активность'}</span></div><h3>{rec.title ?? event?.title ?? rec.event_id}</h3>{session && <p className="session"><CalendarDays size={14} /> Ближайшая сессия: {session}</p>}<p className="rationale">{rec.rationale ?? 'Этот шаг поможет приблизиться к выбранной карьерной цели.'}</p>{rec.factors?.length ? <div className="factor-chips">{rec.factors.map((factor, i) => <span key={i}>{typeof factor === 'string' ? factor : [factor.label ?? factor.name, factor.detail ?? factor.value].filter(Boolean).join(': ')}</span>)}</div> : null}{rec.gains?.length ? <div className="gains">{rec.gains.map((gain, i) => <span key={i}>{name(gain.skill_name ?? gain.skill_id)} {gain.before ?? gain.from ?? '?'} → {gain.after ?? gain.to ?? '?'}</span>)}</div> : null}{rec.readiness_after_pct != null && <p className="after-readiness">Готовность после шага <strong>{pct(rec.readiness_after_pct)}%</strong></p>}<div className="rec-actions"><button className="button primary" disabled={!!busy} onClick={() => onComplete(rec.event_id)}><Check size={16} />{busy === rec.event_id ? 'Обновляем…' : 'Отметить пройденным'}</button><button className="button text" disabled={!!busy} onClick={() => onDecline(rec.event_id)}>Не сейчас</button></div></div>
}
