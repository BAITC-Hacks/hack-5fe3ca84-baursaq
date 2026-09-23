import { useEffect, useMemo, useState } from 'react'
import { BriefcaseBusiness, ChevronDown, Compass, Users } from 'lucide-react'
import { api, type ApiContext } from './api/client'
import type { EmployeeSummary, Language, Role } from './api/view'
import EmployeePage from './pages/EmployeePage'
import HrPage from './pages/HrPage'

function App() {
  const [role, setRole] = useState<Role>('employee')
  const [employeeId, setEmployeeId] = useState('E0028')
  const [language, setLanguage] = useState<Language>('ru')
  const [employees, setEmployees] = useState<EmployeeSummary[]>([])
  const [search, setSearch] = useState('')
  const [pickerOpen, setPickerOpen] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const context: ApiContext = useMemo(() => ({ role, employeeId, language }), [role, employeeId, language])

  useEffect(() => {
    let active = true
    api.employees({ role, employeeId, language }, search)
      .then(items => { if (active) setEmployees(items) })
      .catch(() => { if (active) setEmployees([]) })
    return () => { active = false }
  }, [search, reloadKey, role, employeeId, language])

  const selected = employees.find(item => item.employee_id === employeeId)
  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Compass size={23} strokeWidth={2.3} /></div><div><strong>Career Quest</strong><span>Ваш путь к следующему уровню</span></div></div>
      <div className="top-controls">
        <div className="role-switch" aria-label="Роль">
          <button className={role === 'employee' ? 'active' : ''} onClick={() => setRole('employee')}><BriefcaseBusiness size={16} /> Сотрудник</button>
          <button className={role === 'hr' ? 'active' : ''} onClick={() => setRole('hr')}><Users size={16} /> HR обзор</button>
        </div>
        {role === 'employee' && <div className="picker-wrap">
          <button className="picker-button" onClick={() => setPickerOpen(!pickerOpen)}>{selected?.full_name ?? employeeId}<ChevronDown size={16} /></button>
          {pickerOpen && <div className="picker-menu"><input autoFocus placeholder="Найти сотрудника…" value={search} onChange={event => setSearch(event.target.value)} />
            <div className="picker-list">{employees.length ? employees.slice(0, 30).map(item => <button key={item.employee_id} onClick={() => { setEmployeeId(item.employee_id); setPickerOpen(false); setSearch('') }}><strong>{item.full_name}</strong><span>{item.employee_id} · {item.role} · {item.grade}</span></button>) : <p>Сотрудники не найдены</p>}</div>
          </div>}
        </div>}
        <select className="lang-select" aria-label="Язык" value={language} onChange={event => setLanguage(event.target.value as Language)}><option value="ru">RU</option><option value="kk">KK</option><option value="en">EN</option></select>
      </div>
    </header>
    <main className="page-wrap">
      {role === 'employee' ? <EmployeePage key={`${employeeId}-${reloadKey}`} context={context} /> : <HrPage context={context} onDatasetChange={() => setReloadKey(value => value + 1)} onOpenEmployee={id => { setEmployeeId(id); setRole('employee') }} />}
    </main>
    <footer>Career Quest · Halyk Bank · Данные демонстрационные</footer>
  </div>
}

export default App
