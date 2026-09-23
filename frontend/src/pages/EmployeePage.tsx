import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, CalendarDays, Check, CheckCircle2, Clock3, Compass, RotateCcw, Sparkles, Target, XCircle } from 'lucide-react'
import Readiness from '../components/Readiness'
import LoadingSkeleton from '../components/LoadingSkeleton'
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

  const skills = useMemo(() => profile ? skillsOf(profile).filter(skill => skill.required_level > 0 || skill.critical).sort((a, b) => (b.required_level - b.effective_level) - (a.required_level - a.effective_level) || Number(b.critical) - Number(a.critical)) : [], [profile])
  if (loading && !profile) return <LoadingSkeleton />
  if (!profile) return <div className="empty-state"><XCircle size={34} /><h2>Не удалось открыть профиль</h2><p>{error}</p><button className="button primary" onClick={load}>Повторить</button></div>
  const targetGrade = profile.career_goal?.target_grade ?? profile.target_grade ?? grades[Math.min(grades.indexOf(profile.grade ?? 'Junior') + 1, 3)]
  const targetRole = profile.career_goal?.target_role ?? profile.target_role ?? profile.role
  const history = profile.history ?? []
  const events = profile.available_steps ?? profile.available_events ?? []
  const recs = result?.recommendations ?? []

  return <>
    <div className="page-heading"><div><span className="eyebrow">ВАШЕ РАЗВИТИЕ — В ВАШИХ РУКАХ</span><h1>Следующий шаг — ближе к цели.</h1><p>Персональный план развития с объяснением каждого шага.</p></div><span className="today-badge"><Compass size={16} /> Пространство сотрудника</span></div>
    {error && <div className="alert" role="alert">{error}<button onClick={() => setError('')}>Закрыть</button></div>}
    {toast && <div className="toast" role="status"><span className="toast-spark"><CheckCircle2 size={22} /></span>{toast}</div>}
    <section className="profile-strip">
      <div className="hero-top"><div className="avatar" aria-hidden="true">{profile.full_name.split(' ').map(part => part[0]).slice(0, 2).join('')}</div><div><span className="eyebrow">ВАШ ПРОФИЛЬ · {profile.employee_id}</span><h2>{profile.full_name}</h2><p>{profile.role} <span className="inline-dot">·</span> {profile.grade}</p></div></div>
      <div className="profile-context"><span>{profile.department}</span><span>{profile.tenure_months != null ? `${profile.tenure_months} мес. в компании` : 'Стаж не указан'} · {profile.work_format === 'remote' ? 'Удалённо' : profile.work_format === 'hybrid' ? 'Гибридно' : 'В офисе'}</span></div>
    </section>
    <div className="employee-layout">
      <div className="main-column">
        <section className={`card recommendation-panel ${result ? 'has-plan' : ''}`} aria-busy={recommending}>
          <div className="recommendation-head"><div><span className="eyebrow"><Sparkles size={15} /> AI-НАВИГАТОР</span><h2>Ваш следующий шаг</h2>{!result && <p>Не просто курс. Шаг, который приближает вас к {targetGrade} — с учётом навыков, опыта и вашей цели.</p>}</div><button className={`button ${result ? 'secondary' : 'primary'}`} onClick={recommend} disabled={recommending || !!busy}>{recommending ? 'Подбираем шаги…' : result ? 'Обновить план' : 'Подобрать шаги'}<ArrowRight size={17} /></button></div>
          {!result && !recommending && <div className="plan-intro"><div className="quest-illustration" aria-hidden="true"><span><Compass size={28} /></span><i /><span><Sparkles size={23} /></span><i /><span><Target size={28} /></span></div><div className="intro-labels"><span>Ваш опыт</span><span>Подходящий шаг</span><span>Карьерная цель</span></div><p>Вы выбираете темп. Мы объясняем, что даст каждый шаг.</p></div>}
          {recommending && <div className="plan-loading" role="status"><div className="agent-waiting"><div className="mini-spinner" aria-hidden="true" /><div><strong>Собираем ваш маршрут</strong><p>Сопоставляем цель, навыки и историю участия. Обычно это занимает несколько секунд.</p></div></div><div className="skeleton skeleton-line" /><div className="skeleton skeleton-line short" /><div className="skeleton skeleton-preview" /></div>}
          {result && !recommending && <RecommendationDetails result={result}>
            <div className="plan-cards">{recs.length ? recs.map((rec, index) => <RecommendationCard key={`${rec.event_id}-${index}`} rec={rec} index={index} before={index ? recs[index - 1].readiness_after_pct : profile.readiness_pct} busy={busy} onComplete={complete} onDecline={decline} />) : <div className="empty-mini"><CheckCircle2 size={28} /><strong>Подходящих шагов сейчас нет</strong><p>Текущие навыки и ограничения учтены. Проверьте цель и доступные активности вместе с HR.</p></div>}</div>
          </RecommendationDetails>}
        </section>
        <section className="card skills-card"><div className="section-title"><div><span className="icon-chip"><Compass size={19} /></span><h2>Навыки на пути к цели</h2></div><span className="muted small">Уровни от 0 до 5</span></div><p className="section-description">Сначала — самые большие разрывы. Критичные навыки особенно важны для целевого грейда.</p>
          {skills.length ? [{ title: 'Есть пространство для роста', items: skills.filter(skill => skill.effective_level < skill.required_level) }, { title: 'Уже соответствуют цели', items: skills.filter(skill => skill.effective_level >= skill.required_level) }].filter(group => group.items.length).map(group => <div className="skill-group" key={group.title}><h3>{group.title}<span>{group.items.length}</span></h3><div className="skill-list">{group.items.map(skill => <div className="skill-row" key={skill.skill_id}><div className="skill-label"><strong>{name(skill.name)}</strong>{skill.critical && <span className="critical-tag">Критичный</span>}{skill.effective_level > skill.assessed_level && <span className="gain-tag">+{skill.effective_level - skill.assessed_level} после оценки</span>}</div><div className="skill-values" aria-label={`Эффективный уровень ${skill.effective_level}, требуется ${skill.required_level}`}>{skill.effective_level} <span>/ {skill.required_level}</span></div><div className="skill-track" role="img" aria-label={`${skill.name}: оценка ${skill.assessed_level}, эффективный ${skill.effective_level}, требуется ${skill.required_level}`}><div className="required-marker" style={{ left: `${Math.min(skill.required_level, 5) * 20}%` }} /><div className={skill.effective_level >= skill.required_level ? 'met' : ''} style={{ width: `${Math.min(skill.effective_level, 5) * 20}%` }} /></div></div>)}</div></div>) : <p className="muted">Данные о навыках пока недоступны.</p>}
          <div className="legend"><span><i className="legend-fill" /> Эффективный уровень</span><span><i className="legend-line" /> Требуется для цели</span></div><p className="muted small">Эффективный уровень = последняя оценка + пройденное после неё</p>
        </section>
      </div>
      <aside className="side-column">
        <section className="card trajectory-card"><div className="section-title"><div><span className="icon-chip"><Target size={19} /></span><h2>Ваша цель</h2></div></div><div className="goal-overview"><Readiness value={pct(profile.readiness_pct)} /><div><span className="eyebrow">КУДА ДВИЖЕМСЯ</span><h3>{targetGrade}</h3><p>{targetRole}</p></div></div><p className="readiness-caption">Доля выполненных требований цели. Прогресс обучения, а не гарантия повышения.</p><div className="trajectory-line" aria-label="Карьерная траектория">{grades.map((grade, index) => <div key={grade} className={`grade-node ${grade === profile.grade ? 'current' : ''} ${grades.indexOf(profile.grade ?? '') > index ? 'passed' : ''} ${grade === targetGrade ? 'target' : ''}`}><div className="node-dot">{grades.indexOf(profile.grade ?? '') > index ? <Check size={15} /> : grade === targetGrade ? <Target size={16} /> : <span />}</div><strong>{grade}</strong><span>{grade === profile.grade && grade === targetGrade ? 'Сейчас / цель' : grade === profile.grade ? 'Вы здесь' : grade === targetGrade ? 'Цель' : ''}</span></div>)}</div>{targetRole !== profile.role && <p className="role-change">Смена роли: {profile.role} → {targetRole}</p>}</section>
        <section className="card history-card"><div className="section-title"><div><span className="icon-chip"><Clock3 size={19} /></span><h2>История участия</h2></div><span className="muted small">{history.length} записей</span></div>{history.length ? <div className="history-list">{history.slice().sort((a, b) => (b.date ?? '').localeCompare(a.date ?? '')).slice(0, 8).map((item, index) => <div key={`${item.event_id}-${index}`} className="history-item"><span className={`history-dot ${item.status}`} /><div><strong>{item.title ?? item.event_id}</strong><span>{item.date ?? 'Дата не указана'}</span></div><span className={`status ${item.status}`}>{statuses[item.status] ?? item.status}</span></div>)}</div> : <p className="muted">Здесь появится ваша первая пройденная активность.</p>}</section>
        <section className="card steps-card"><details><summary><RotateCcw size={18} /> Доступные шаги <span>{events.length}</span></summary>{events.length ? events.slice(0, 6).map(event => <div className="available-item" key={event.event_id}><strong>{event.title}</strong><span>{formats[event.format ?? ''] ?? event.format ?? 'Активность'}{event.duration_hours ? ` · ${event.duration_hours} ч` : ''}</span></div>) : <p className="muted">Новых доступных активностей пока нет.</p>}</details></section>
      </aside>
    </div>
  </>
}

function RecommendationCard({ rec, index, before, busy, onComplete, onDecline }: { rec: Recommendation; index: number; before?: number; busy: string | null; onComplete: (id: string) => void; onDecline: (id: string) => void }) {
  const [showAllFactors, setShowAllFactors] = useState(false)
  const factors = [...(rec.factors ?? [])].sort((a, b) =>
    Math.abs(typeof b === 'string' ? 0 : b.impact ?? 0) - Math.abs(typeof a === 'string' ? 0 : a.impact ?? 0))
  const event: EventItem | undefined = rec.event
  const session = (rec.upcoming_sessions ?? event?.upcoming_sessions)?.[0]
  return <article className={`rec-card ${index === 0 ? 'rec-featured' : 'rec-compact'}`}><div className="rec-top"><span className="rec-number">ШАГ {index + 1}{index === 0 ? ' · НАЧНИТЕ ЗДЕСЬ' : ' · ДАЛЕЕ ПО ПЛАНУ'}</span><span className="format-tag">{formats[rec.format ?? event?.format ?? ''] ?? rec.format ?? event?.format ?? 'Активность'}</span></div><h3>{rec.title ?? event?.title ?? rec.event_id}</h3>{session && <p className="session"><CalendarDays size={14} /> Ближайшая сессия: {session}</p>}<p className="rationale">{rec.rationale?.match(/^[\s\S]*?[.!?](?:\s|$)/)?.[0] ?? rec.rationale}</p>{rec.rationale && rec.rationale !== rec.rationale.match(/^[\s\S]*?[.!?](?:\s|$)/)?.[0]?.trim() && <details className="rationale-details"><summary>Полное объяснение</summary><p>{rec.rationale}</p></details>}{factors.length > 0 && <><div className="factor-chips">{factors.slice(0, 3).map((factor, i) => <span key={i}>{typeof factor === 'string' ? factor : [factor.label ?? factor.name, factor.detail ?? factor.value].filter(Boolean).join(': ')}</span>)}</div>{factors.length > 3 && <><button className="button text" aria-expanded={showAllFactors} onClick={() => setShowAllFactors(value => !value)}>{showAllFactors ? 'Скрыть дополнительные факторы' : `ещё ${factors.length - 3} факторов`}</button>{showAllFactors && <div className="factor-chips">{factors.slice(3).map((factor, i) => <span key={i}>{typeof factor === 'string' ? factor : [factor.label ?? factor.name, factor.detail ?? factor.value].filter(Boolean).join(': ')}</span>)}</div>}</>}</>}{rec.gains?.length ? <div className="gains">{rec.gains.map((gain, i) => <span key={i}>{name(gain.skill_name ?? gain.skill_id)} {gain.before ?? gain.from ?? '?'} → {gain.after ?? gain.to ?? '?'}</span>)}</div> : null}{rec.readiness_after_pct != null && <div className="readiness-projection"><div className="after-readiness"><span>Готовность после шага</span><strong>{before != null && <span>{pct(before)}% → </span>}{pct(rec.readiness_after_pct)}%</strong></div><div className="projection-track" aria-hidden="true"><div style={{ width: `${pct(rec.readiness_after_pct)}%` }} /><div style={{ width: `${pct(before)}%` }} /></div></div>}<div className="rec-actions"><button className="button primary" disabled={!!busy} onClick={() => onComplete(rec.event_id)}><Check size={16} />{busy === rec.event_id ? 'Обновляем…' : 'Отметить пройденным'}</button><button className="button text" disabled={!!busy} onClick={() => onDecline(rec.event_id)}>Не сейчас</button></div><p className="muted small">Добровольный шаг · В демо вы отмечаете прохождение сами</p></article>
}
