import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, BarChart3, RotateCcw, UploadCloud, Users, Compass, CalendarCheck, Route, HeartHandshake } from 'lucide-react'
import { api, type ApiContext } from '../api/client'
import type { UploadResult } from '../api/types'
import type { HrOverview } from '../api/view'
import LoadingSkeleton from '../components/LoadingSkeleton'
import SkillChart from '../components/SkillChart'

const acceptedFiles = ['employees.json', 'activity_history.csv', 'events.json', 'skills.json']

export default function HrPage({ context, onDatasetChange, onOpenEmployee }: {
  context: ApiContext
  onDatasetChange: () => void
  onOpenEmployee: (id: string) => void
}) {
  const [overview, setOverview] = useState<HrOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<'upload' | 'reset' | null>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null)
  const [onlyVoluntary, setOnlyVoluntary] = useState(true)
  const fileInput = useRef<HTMLInputElement>(null)
  const mutationPending = useRef(false)

  useEffect(() => {
    let active = true
    api.hr(context)
      .then(data => { if (active) setOverview(data) })
      .catch(cause => { if (active) setError((cause as Error).message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [context])

  const load = async () => {
    setLoading(true); setError('')
    try { setOverview(await api.hr(context)) }
    catch (cause) { setError((cause as Error).message) }
    finally { setLoading(false) }
  }

  const upload = async (files: File[]) => {
    if (!files.length || mutationPending.current) return
    const invalid = files.filter(file => !acceptedFiles.includes(file.name))
    if (invalid.length) {
      setError(`Неизвестные файлы: ${invalid.map(file => file.name).join(', ')}. Выберите ${acceptedFiles.join(', ')}.`)
      return
    }
    mutationPending.current = true
    setBusy('upload'); setError(''); setMessage(''); setUploadResult(null)
    try {
      const result = await api.upload(files, context)
      setUploadResult(result)
      const added = Object.values(result.added).reduce((sum, count) => sum + count, 0)
      const updated = Object.values(result.updated).reduce((sum, count) => sum + count, 0)
      setMessage(`Загрузка завершена. Добавлено записей: ${added}, обновлено: ${updated}.`)
      onDatasetChange()
      await load()
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(null); mutationPending.current = false }
  }

  const reset = async () => {
    if (mutationPending.current) return
    mutationPending.current = true
    setBusy('reset'); setError(''); setMessage('')
    try {
      await api.reset(context)
      setUploadResult(null); setMessage('Исходный датасет восстановлен.')
      onDatasetChange()
      await load()
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(null); mutationPending.current = false }
  }

  const skills = overview?.lagging_skills ?? overview?.skill_gaps ?? []
  const participation = overview?.participation ?? []
  const visibleParticipation = participation.filter(item => !onlyVoluntary || !item.mandatory)
  const noStep = overview?.no_next_step ?? overview?.without_recommendations ?? []
  const disengaged = overview?.disengaged ?? []
  const chart = [...skills].sort((a, b) => (b.count ?? b.employee_count ?? 0) - (a.count ?? a.employee_count ?? 0)).slice(0, 8).map(skill => ({
    name: skill.name ?? skill.skill_name ?? skill.skill_id?.replace(/^SK_/, '').replaceAll('_', ' ') ?? 'Навык',
    count: skill.count ?? skill.employee_count ?? 0,
  }))

  return <>
    <div className="page-heading">
      <div><span className="eyebrow">АНАЛИТИКА КОМАНДЫ</span><h1>Обзор для HR</h1><p>Где команде нужна поддержка и какие шаги работают.</p></div>
      <span className="today-badge"><Users size={16} /> Доступно только HR</span>
    </div>
    {error && <div className="alert" role="alert">{error}<button onClick={() => setError('')}>Закрыть</button></div>}
    {message && <div className="success-note" role="status">{message}</div>}
    {loading && !overview && <LoadingSkeleton label="Загружаем обзор развития команды…" />}
    {loading && overview && <div className="refresh-status" role="status"><div className="mini-spinner" /> Загружаем аналитику…</div>}
    {!loading && !overview && <div className="empty-state"><h2>Не удалось загрузить аналитику</h2><button className="button primary" onClick={load}>Повторить</button></div>}
    {overview && <div className="hr-summary">
      <div className="summary-card"><span className="kpi-icon"><Compass size={20} /></span><span>Навыков с разрывом</span><strong>{skills.length}</strong><small>есть потребность в развитии</small></div>
      <div className="summary-card"><span className="kpi-icon"><CalendarCheck size={20} /></span><span>Активностей в отчёте</span><strong>{participation.length}</strong><small>по истории участия</small></div>
      <div className="summary-card"><span className="kpi-icon"><Route size={20} /></span><span>Без следующего шага</span><strong>{noStep.length}</strong><small>нужна проверка цели</small></div>
      <div className="summary-card attention"><span className="kpi-icon"><HeartHandshake size={20} /></span><span>Требуют внимания</span><strong>{disengaged.length}</strong><small>повод предложить поддержку</small></div>
    </div>}
    {overview && <div className="hr-grid">
      <section className="card">
        <div className="section-title"><div><span className="icon-chip"><BarChart3 size={19} /></span><h2>Чаще всего отстают</h2></div></div>
        <p className="muted">Сотрудников с разрывом до целевого уровня навыка</p>
        {chart.length ? <SkillChart data={chart} /> : <p className="muted">{overview ? 'Разрывов навыков пока нет.' : 'Ожидаем данные аналитики.'}</p>}
      </section>
      <section className="card">
        <div className="section-title"><div><span className="icon-chip"><UploadCloud size={19} /></span><h2>Загрузка профилей</h2></div></div>
        <p className="muted">Добавьте профили JSON и историю CSV вместе — рекомендации учтут опыт новых сотрудников.</p>
        <div className={`drop-zone ${dragging ? 'dragging' : ''}`} aria-busy={!!busy}
          onDragOver={event => { event.preventDefault(); if (!busy) setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={event => { event.preventDefault(); setDragging(false); void upload(Array.from(event.dataTransfer.files)) }}>
          <UploadCloud size={28} aria-hidden="true" />
          <strong>{busy === 'upload' ? 'Загружаем файлы…' : 'Перетащите файлы сюда'}</strong>
          <span>employees.json + activity_history.csv</span><small>Также поддерживаются events.json и skills.json</small>
          <button className="button secondary" onClick={() => fileInput.current?.click()} disabled={!!busy}>Выбрать файлы</button>
          <input ref={fileInput} type="file" aria-label="Файлы датасета" multiple accept=".json,.csv" hidden
            onChange={event => { void upload(Array.from(event.target.files ?? [])); event.target.value = '' }} disabled={!!busy} />
        </div>
        {uploadResult && <div className="upload-report" aria-live="polite">
          {uploadResult.employee_ids.length > 0 && <div className="uploaded-links">
            <strong>Загруженные профили ({uploadResult.employee_ids.length})</strong>
            {uploadResult.employee_ids.map(id => <button key={id} onClick={() => onOpenEmployee(id)} aria-label={`Открыть профиль ${id}`}>{id} →</button>)}
          </div>}
          {uploadResult.warnings.length > 0 && <div className="upload-warnings">
            <strong><AlertTriangle size={16} /> Замечания к загрузке</strong>
            <ul>{uploadResult.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>
          </div>}
        </div>}
        <button className="button text reset-button" disabled={!!busy} onClick={reset}><RotateCcw size={15} />{busy === 'reset' ? 'Восстанавливаем…' : 'Восстановить исходные данные'}</button>
      </section>
    </div>}
    {overview && <div className="hr-grid">
      <section className="card participation-card">
        <div className="section-title"><div><span className="icon-chip"><Users size={19} /></span><h2>Участие по активностям</h2></div></div>
        <label className="participation-filter"><input type="checkbox" checked={onlyVoluntary} onChange={event => setOnlyVoluntary(event.target.checked)} /> Только добровольные</label>
        <p className="muted small">Показано {visibleParticipation.length} из {participation.length} активностей</p>
        {visibleParticipation.length ? <div className="table-scroll" tabIndex={0} aria-label="Таблица участия по активностям">
          <table><thead><tr><th scope="col">Активность</th><th scope="col">Пройдено</th><th scope="col">Не пришли</th><th scope="col">Отказ</th><th scope="col">В процессе</th><th scope="col">Прервано</th><th scope="col">Просрочено</th></tr></thead>
            <tbody>{visibleParticipation.map(item => <tr key={item.event_id}>
              <td>{item.title}{item.mandatory && <span className="mandatory-badge">Обязательное</span>}</td>
              <td>{item.completed}</td><td>{item.no_show}</td><td>{item.declined}</td><td>{item.in_progress}</td><td>{item.dropped}</td><td>{item.overdue}</td>
            </tr>)}</tbody>
          </table>
        </div> : <p className="muted">{onlyVoluntary ? 'Добровольных активностей в отчёте пока нет. Снимите фильтр, чтобы увидеть все.' : 'Данных об участии пока нет.'}</p>}
      </section>
      <section className="card">
        <div className="section-title"><div><span className="icon-chip"><Users size={19} /></span><h2>Нужна поддержка</h2></div></div>
        <h3 className="list-heading">Нет подходящего шага</h3>
        {noStep.length ? <div className="people-list">{noStep.map((item, index) => <div key={item.employee_id ?? index}>
          <button onClick={() => item.employee_id && onOpenEmployee(item.employee_id)}>{item.full_name ?? item.employee_id}</button><span>{item.reason ?? 'Проверьте цель и доступные активности'}</span>
        </div>)}</div> : <p className="muted">Для всех есть доступный шаг.</p>}
        <h3 className="list-heading">Снижается участие</h3>
        {disengaged.length ? <div className="people-list">{disengaged.map((item, index) => <div key={item.employee_id ?? index}>
          <button onClick={() => item.employee_id && onOpenEmployee(item.employee_id)}>{item.full_name ?? item.employee_id}</button><span>{item.reason ?? 'Нужен личный разговор о предпочтениях'}</span>
        </div>)}</div> : <p className="muted">Нет сотрудников, требующих внимания.</p>}
      </section>
    </div>}
  </>
}
