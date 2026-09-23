import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { BriefcaseBusiness, ChevronDown, Users } from 'lucide-react'
import { api, type ApiContext } from './api/client'
import type { EmployeeSummary, Language, Role } from './api/view'
import EmployeePage from './pages/EmployeePage'
const HrPage = lazy(() => import('./pages/HrPage'))

function App() {
  const [role, setRole] = useState<Role>('employee')
  const [employeeId, setEmployeeId] = useState('E0072')
  const [language, setLanguage] = useState<Language>('ru')
  const [employees, setEmployees] = useState<EmployeeSummary[]>([])
  const [search, setSearch] = useState('')
  const [pickerOpen, setPickerOpen] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [directoryError, setDirectoryError] = useState('')
  const [directoryLoading, setDirectoryLoading] = useState(true)
  const context: ApiContext = useMemo(() => ({ role, employeeId, language }), [role, employeeId, language])

  useEffect(() => {
    let active = true
    api.employees({ role, employeeId, language }, search)
      .then(items => { if (active) { setEmployees(items); setDirectoryError('') } })
      .catch(() => { if (active) { setEmployees([]); setDirectoryError('Не удалось загрузить список сотрудников.') } })
      .finally(() => { if (active) setDirectoryLoading(false) })
    return () => { active = false }
  }, [search, reloadKey, role, employeeId, language])

  const selected = employees.find(item => item.employee_id === employeeId)
  return <div className="app-shell"><a className="skip-link" href="#main-content">Перейти к содержимому</a>
    <header className="topbar">
      <div className="brand"><img src="/halyk-logo.png" alt="" width={40} height={40} /><div><strong>Career Quest</strong><span>Навигатор карьерного развития</span></div></div>
      <div className="top-controls">
        <div className="role-switch" role="group" aria-label="Роль">
          <button aria-pressed={role === 'employee'} className={role === 'employee' ? 'active' : ''} onClick={() => setRole('employee')}><BriefcaseBusiness size={16} /> Сотрудник</button>
          <button aria-pressed={role === 'hr'} className={role === 'hr' ? 'active' : ''} onClick={() => setRole('hr')}><Users size={16} /> HR обзор</button>
        </div>
        {role === 'employee' && <div className="picker-wrap">
          <button className="picker-button" aria-expanded={pickerOpen} onClick={() => setPickerOpen(!pickerOpen)}>{selected?.full_name ?? employeeId}<ChevronDown size={16} /></button>
          {pickerOpen && <div className="picker-menu" onKeyDown={event => { if (event.key === 'Escape') setPickerOpen(false) }}><input autoFocus aria-label="Найти сотрудника" placeholder="Найти сотрудника…" value={search} onChange={event => { setDirectoryLoading(true); setSearch(event.target.value) }} />
            <div className="picker-list">{directoryLoading ? <p role="status">Ищем сотрудников…</p> : directoryError ? <div role="alert"><p>{directoryError}</p><button onClick={() => { setDirectoryLoading(true); setReloadKey(value => value + 1) }}>Повторить поиск</button></div> : employees.length ? employees.slice(0, 30).map(item => <button key={item.employee_id} onClick={() => { setEmployeeId(item.employee_id); setPickerOpen(false); setSearch('') }}><strong>{item.full_name}</strong><span>{item.employee_id} · {item.role} · {item.grade}</span></button>) : <p>Сотрудники не найдены</p>}</div>
          </div>}
        </div>}
        <select className="lang-select" aria-label="Язык ответа ИИ" title="Язык объяснений ИИ. Интерфейс — на русском." value={language} onChange={event => setLanguage(event.target.value as Language)}><option value="ru">ИИ: RU</option><option value="kk">ИИ: KK</option><option value="en">ИИ: EN</option></select>
      </div>
    </header>
    <main id="main-content" className="page-wrap" tabIndex={-1}>
      <Suspense fallback={<div className="loading-panel" role="status"><div className="spinner" /> Загружаем HR-обзор…</div>}>
        {role === 'employee' ? <EmployeePage key={`${employeeId}-${language}-${reloadKey}`} context={context} /> : <HrPage key={language} context={context} onDatasetChange={() => setReloadKey(value => value + 1)} onOpenEmployee={id => { setEmployeeId(id); setRole('employee') }} />}
      </Suspense>
    </main>
    <footer>Career Quest · Развитие в вашем темпе. Все данные демонстрационные.</footer>
  </div>
}

export default App
