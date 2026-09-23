import { useCallback, useEffect, useState } from 'react'
import { BarChart3, RotateCcw, UploadCloud, Users, XCircle } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, type ApiContext } from '../api/client'
import type { HrOverview } from '../api/view'

export default function HrPage({ context, onDatasetChange, onOpenEmployee }: { context: ApiContext; onDatasetChange: () => void; onOpenEmployee: (id: string) => void }) {
  const [overview, setOverview] = useState<HrOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [uploaded, setUploaded] = useState<string[]>([])
  const load = useCallback(async () => { setLoading(true); setError(''); try { setOverview(await api.hr(context)) } catch (cause) { setError((cause as Error).message) } finally { setLoading(false) } }, [context])
  useEffect(() => { void load() }, [load])

  const upload = async (files: File[]) => {
    if (!files.length) return
    const valid = files.filter(file => ['employees.json', 'activity_history.csv', 'events.json', 'skills.json'].includes(file.name))
    if (!valid.length) { setError('Выберите файлы employees.json, activity_history.csv, events.json или skills.json.'); return }
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await api.upload(valid, context)
      const ids = findIds(result)
      setUploaded(ids)
      setMessage(`Загружено файлов: ${valid.length}. Данные обновлены.`)
      onDatasetChange(); await load()
    } catch (cause) { setError((cause as Error).message) }
    finally { setBusy(false) }
  }
  const reset = async () => {
    setBusy(true); setError(''); setMessage('')
    try { await api.reset(context); setUploaded([]); setMessage('Исходный датасет восстановлен.'); onDatasetChange(); await load() }
    catch (cause) { setError((cause as Error).message) }
    finally { setBusy(false) }
  }

  const skills = overview?.lagging_skills ?? overview?.skill_gaps ?? []
  const participation = overview?.participation ?? []
  const noStep = overview?.no_next_step ?? overview?.without_recommendations ?? []
  const disengaged = overview?.disengaged ?? []
  const chart = skills.slice(0, 8).map(skill => ({ name: skill.name ?? skill.skill_name ?? skill.skill_id?.replace(/^SK_/, '').replaceAll('_', ' ') ?? 'Навык', count: skill.count ?? skill.employee_count ?? 0 }))
  return <>
    <div className="page-heading"><div><span className="eyebrow">АНАЛИТИКА КОМАНДЫ</span><h1>Обзор для HR</h1><p>Где команде нужна поддержка и какие шаги работают.</p></div><span className="today-badge"><Users size={16} /> Доступно только HR</span></div>
    {error && <div className="alert" role="alert">{error}<button onClick={() => setError('')}>Закрыть</button></div>}
    {message && <div className="success-note" role="status">{message}</div>}
    {loading && !overview ? <div className="loading-panel"><div className="spinner" /> Загружаем аналитику…</div> : !overview ? <div className="empty-state"><XCircle size={34} /><h2>Нет данных HR</h2><button className="button primary" onClick={load}>Повторить</button></div> : <>
      <div className="hr-summary"><div className="summary-card"><span>Навыков с разрывом</span><strong>{skills.length}</strong><small>в целевых профилях</small></div><div className="summary-card"><span>Активностей в отчёте</span><strong>{participation.length}</strong><small>по истории участия</small></div><div className="summary-card"><span>Без следующего шага</span><strong>{noStep.length}</strong><small>нужна проверка цели</small></div><div className="summary-card"><span>Требуют внимания</span><strong>{disengaged.length}</strong><small>участие снизилось</small></div></div>
      <div className="hr-grid"><section className="card"><div className="section-title"><div><span className="icon-chip"><BarChart3 size={19} /></span><h2>Чаще всего отстают</h2></div></div>{chart.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart} layout="vertical" margin={{ left: 12, right: 16 }}><CartesianGrid stroke="#edf1ed" horizontal={false} /><XAxis type="number" allowDecimals={false} tick={{ fill: '#7e8b85', fontSize: 12 }} /><YAxis type="category" dataKey="name" width={150} tick={{ fill: '#33443a', fontSize: 12 }} /><Tooltip /><Bar dataKey="count" fill="#00805f" radius={[0, 6, 6, 0]} name="Сотрудников" /></BarChart></ResponsiveContainer></div> : <p className="muted">Разрывов навыков пока нет.</p>}</section>
      <section className="card"><div className="section-title"><div><span className="icon-chip"><UploadCloud size={19} /></span><h2>Загрузка профилей</h2></div></div><p className="muted">Добавьте профили и историю в формате датасета. Новые сотрудники появятся в поиске.</p><div className={`drop-zone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); void upload(Array.from(event.dataTransfer.files)) }}><UploadCloud size={28} /><strong>Перетащите файлы сюда</strong><span>employees.json · activity_history.csv · events.json · skills.json</span><label className="button secondary">Выбрать файлы<input type="file" multiple accept=".json,.csv" onChange={event => { void upload(Array.from(event.target.files ?? [])); event.target.value = '' }} disabled={busy} /></label></div>{uploaded.length > 0 && <div className="uploaded-links"><strong>Загруженные профили</strong>{uploaded.map(id => <button key={id} onClick={() => onOpenEmployee(id)}>{id} →</button>)}</div>}<button className="button text reset-button" disabled={busy} onClick={reset}><RotateCcw size={15} /> Восстановить исходные данные</button></section></div>
      <div className="hr-grid"><section className="card"><div className="section-title"><div><span className="icon-chip"><Users size={19} /></span><h2>Участие по активностям</h2></div></div>{participation.length ? <div className="table-scroll"><table><thead><tr><th>Активность</th><th>Пройдено</th><th>Не пришли</th><th>Отказ</th></tr></thead><tbody>{participation.map((item, index) => <tr key={item.event_id ?? index}><td>{item.title ?? item.event_title ?? item.event_id}</td><td>{item.completed ?? item.count ?? 0}</td><td>{item.no_show ?? 0}</td><td>{item.declined ?? 0}</td></tr>)}</tbody></table></div> : <p className="muted">Данных об участии пока нет.</p>}</section><section className="card"><div className="section-title"><div><span className="icon-chip"><Users size={19} /></span><h2>Нужна поддержка</h2></div></div><h3 className="list-heading">Нет подходящего шага</h3>{noStep.length ? <div className="people-list">{noStep.map((item, index) => <div key={item.employee_id ?? index}><button onClick={() => item.employee_id && onOpenEmployee(item.employee_id)}>{item.full_name ?? item.employee_id}</button><span>{item.reason ?? 'Проверьте цель и доступные активности'}</span></div>)}</div> : <p className="muted">Для всех есть доступный шаг.</p>}<h3 className="list-heading">Снижается участие</h3>{disengaged.length ? <div className="people-list">{disengaged.map((item, index) => <div key={item.employee_id ?? index}><button onClick={() => item.employee_id && onOpenEmployee(item.employee_id)}>{item.full_name ?? item.employee_id}</button><span>{item.reason ?? 'Нужен личный разговор о предпочтениях'}</span></div>)}</div> : <p className="muted">Нет сотрудников, требующих внимания.</p>}</section></div>
    </>}
  </>
}

function findIds(value: unknown): string[] {
  if (!value || typeof value !== 'object') return []
  const body = value as Record<string, unknown>
  for (const key of ['employee_ids', 'uploaded_employee_ids', 'employees']) {
    const list = body[key]
    if (Array.isArray(list)) return list.map(item => typeof item === 'string' ? item : typeof item === 'object' && item !== null ? String((item as Record<string, unknown>).employee_id ?? '') : '').filter(Boolean)
  }
  return []
}
