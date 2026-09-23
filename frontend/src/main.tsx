import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { api } from './api';
import type { Person, Profile, Result, HR, Session } from './types';
import './style.css';

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [role, setRole] = useState<'employee' | 'hr'>('employee');
  const [password, setPassword] = useState('employee-demo');
  const [accounts, setAccounts] = useState<Person[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [selected, setSelected] = useState('E0001');
  const [profile, setProfile] = useState<Profile | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [hr, setHR] = useState<HR | null>(null);
  const [tab, setTab] = useState<'profile' | 'hr'>('profile');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const token = session?.token || '';

  useEffect(() => { api<Person[]>('/demo/accounts').then(setAccounts).catch(e => setError(e.message)); }, []);
  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    api<Person[]>('/employees', session.token).then(rows => {
      if (!cancelled) { setPeople(rows); setSelected(session.employee_id || rows[0]?.employee_id || ''); }
    }).catch(e => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [session]);
  useEffect(() => {
    if (!token || !selected) return;
    let cancelled = false;
    setProfile(null); setResult(null); setError('');
    api<Profile>(`/employees/${encodeURIComponent(selected)}`, token)
      .then(data => { if (!cancelled) setProfile(data); }).catch(e => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [selected, token]);
  useEffect(() => {
    if (tab !== 'hr' || !token) return;
    let cancelled = false;
    setHR(null);
    api<HR>('/hr/summary', token).then(data => { if (!cancelled) setHR(data); }).catch(e => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; };
  }, [tab, token]);

  async function action(fn: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await fn(); } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function login(event: React.FormEvent) {
    event.preventDefault();
    await action(async () => {
      const loginSession = await api<Session>('/auth/login', '', {method: 'POST', body: JSON.stringify({role, employee_id: selected, password})});
      setProfile(null); setResult(null); setSession(loginSession);
    });
  }
  async function complete(eventId: string) {
    await action(async () => {
      const response = await api<{changed: boolean; profile: Profile}>(`/employees/${encodeURIComponent(selected)}/complete`, token,
        {method: 'POST', body: JSON.stringify({event_id: eventId})});
      setProfile(response.profile); setResult(null); setHR(null);
      setNotice(response.changed ? 'Активность завершена. Навыки и прогресс обновлены.' : 'Эта активность уже учтена.');
    });
  }
  async function importData(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const history = data.get('history');
    if (history instanceof File && !history.size) data.delete('history');
    await action(async () => {
      const imported = await api<{employees_imported: number; history_imported: number}>('/import', token, {method: 'POST', body: data});
      setPeople(await api<Person[]>('/employees', token)); setHR(await api<HR>('/hr/summary', token));
      if (selected) setProfile(await api<Profile>(`/employees/${encodeURIComponent(selected)}`, token));
      setResult(null);
      setNotice(`Загружено профилей: ${imported.employees_imported}; записей истории: ${imported.history_imported}.`);
    });
  }
  const employeeOptions = (rows: Person[]) => rows.map(p => <option key={p.employee_id} value={p.employee_id}>{p.full_name} · {p.employee_id}</option>);

  if (!session) return <main className="login-layout">
    <section className="intro"><div className="brand">CQ <span>Career Quest</span></div><p className="eyebrow">BAURSAQ · HACKALEM AI</p>
      <h1>Развитие, у которого<br/>есть направление.</h1><p>Ваши навыки, карьерная цель и следующий шаг — в одном месте.</p>
      <div className="intro-line">01 &nbsp; Узнайте разрывы<br/>02 &nbsp; Выберите подходящий шаг<br/>03 &nbsp; Увидьте свой прогресс</div>
    </section>
    <form className="login-card" onSubmit={login}><p className="eyebrow">ДЕМОНСТРАЦИОННЫЙ ВХОД</p><h2>Начнём с вашего профиля</h2>
      <label>Роль<select value={role} onChange={e => { const v=e.target.value as 'employee'|'hr'; setRole(v); setPassword(v==='hr'?'hr-demo':'employee-demo'); }}><option value="employee">Сотрудник</option><option value="hr">HR</option></select></label>
      {role==='employee' && <label>Сотрудник<select value={selected} onChange={e=>setSelected(e.target.value)}>{employeeOptions(accounts)}</select></label>}
      <label>Демо-пароль<input type="password" value={password} onChange={e=>setPassword(e.target.value)}/></label>
      <button disabled={busy || !accounts.length}>{busy?'Входим…':'Открыть пространство →'}</button>
      <small>Синтетические профили из набора хакатона. Персональные данные реальных сотрудников не используются.</small>
      {error && <p role="alert" className="error">{error}</p>}
    </form>
  </main>;

  return <div className="workspace">
    <aside><div className="brand">CQ <span>Career Quest</span></div><p className="eyebrow">МОЁ ПРОСТРАНСТВО</p>
      <button className={tab==='profile'?'nav active':'nav'} onClick={()=>setTab('profile')}>Траектория развития</button>
      {session.role==='hr' && <button className={tab==='hr'?'nav active':'nav'} onClick={()=>setTab('hr')}>Обзор HR</button>}
      <div className="aside-bottom"><p>baursaq / HackAlem AI</p><button className="nav" disabled={busy} onClick={()=>action(async()=>{
        await api('/auth/logout',token,{method:'POST'});setSession(null);setProfile(null);setResult(null);setTab('profile');
      })}>Выйти</button></div>
    </aside>
    <main className="content"><header><div><p className="eyebrow">{tab==='hr'?'РАЗВИТИЕ КОМАНДЫ':'ВАШ СЛЕДУЮЩИЙ ШАГ'}</p>
      <h1>{tab==='hr'?'Обзор компетенций':'Карьерная траектория'}</h1></div><span className="badge">Срез: 01.10.2026</span></header>
      {error && <p role="alert" className="error">{error}</p>}{notice && <p role="status" className="notice">{notice}</p>}
      {tab==='profile' && <>
        <label className="person-select">Профиль<select disabled={busy} value={selected} onChange={e=>setSelected(e.target.value)}>{employeeOptions(people)}</select></label>
        {!profile?<p aria-live="polite">Загружаем профиль…</p>:<>
          <section className="card profile-hero"><div><p className="eyebrow">{profile.employee.department}</p><h2>{profile.employee.full_name}</h2>
            <p>{profile.employee.role} · {profile.employee.grade}</p><p>Цель: <strong>{profile.target.role} / {profile.target.grade}</strong></p></div>
            <div className="progress-box"><strong>{profile.progress_pct}%</strong><span>требований цели покрыто</span><progress max="100" value={profile.progress_pct}/></div>
          </section>
          <section className="section-title"><div><h2>Рекомендуемые шаги</h2><p>Навыки, требования цели и история участия вместе.</p></div>
            <button disabled={busy} onClick={()=>action(async()=>setResult(await api<Result>(`/employees/${encodeURIComponent(selected)}/recommendations`,token,{method:'POST',body:JSON.stringify({language:'ru'})})))}>{busy?'Подбираем…':'Подобрать шаги →'}</button>
          </section>
          {result && <><p className={result.mode==='rules'?'warning':'notice'}>{result.mode==='rules'?'Подбор по правилам':'OpenAI-рекомендация'} · {result.duration_ms} мс{result.warning && ` — ${result.warning}`}</p>
            {result.empty_reason && <p>{result.empty_reason}</p>}
            <div className="recommendations">{result.recommendations.map((r,i)=><article className="card recommendation" key={r.event_id}>
              <span className="eyebrow">ШАГ 0{i+1} · {r.format} · {r.duration_hours} ч</span><h3>{r.title}</h3><p>{r.reason}</p>
              <div className="gain">{r.projection.changes.map(c=><span key={c.name}>{c.name}: {c.before} → {c.after}</span>)}</div>
              <p>Покрытие цели: {r.projection.progress_before}% → <strong>{r.projection.progress_after}%</strong></p>
              <details><summary>На каких данных основано</summary>{r.evidence.map(e=><p key={e.factor}>{e.text}<small>{e.source}</small></p>)}</details>
              <button disabled={busy} onClick={()=>complete(r.event_id)}>Отметить выполненным</button>
            </article>)}</div>
            <details className="card trace"><summary>Как получен результат · {result.trace.length} шагов</summary>{result.trace.map((t,i)=><p key={i}><strong>{t.tool}</strong> · {t.duration_ms} мс<br/>{t.summary}</p>)}</details>
          </>}
          <section className="card"><h2>Карта навыков</h2><p>Критичные навыки отмечены точкой. Повышение грейда обсуждается с руководителем.</p>
            <div className="skill-grid">{profile.skills.filter(s=>s.required>0).map(s=><div className="skill" key={s.skill_id}><div><span>{s.critical?'● ':''}{s.name}</span><strong>{s.current} / {s.required}</strong></div><progress max="5" value={s.current}/><small>{s.gap?`До цели: +${s.gap}`:'Требование выполнено'}</small></div>)}</div>
          </section>
          <section className="card"><h2>История развития</h2><div className="table-wrap"><table><thead><tr><th>Активность</th><th>Дата</th><th>Статус</th></tr></thead><tbody>{profile.history.map(h=><tr key={h.record_id}><td>{h.title}</td><td>{h.date}</td><td>{h.status}</td></tr>)}</tbody></table>{!profile.history.length&&<p>История пока пуста.</p>}</div></section>
        </>}
      </>}
      {tab==='hr' && <>
        <section className="card"><h2>Проверочные данные</h2><p>Загрузите профили JSON и историю CSV в формате стартового набора.</p><form className="import-form" onSubmit={importData}>
          <label>Профили JSON<input type="file" name="employees" accept=".json" required/></label><label>История CSV<input type="file" name="history" accept=".csv"/></label><button disabled={busy}>Загрузить</button></form></section>
        {!hr?<p>Считаем обзор…</p>:<><p>Сотрудников: <strong>{hr.employee_count}</strong> · Без доступного шага: <strong>{hr.no_next_step.length}</strong></p>
          <section className="card"><h2>Частые разрывы по навыкам</h2><div className="skill-grid">{hr.skill_gaps.slice(0,12).map(s=><div className="skill" key={s.skill_id}><div><span>{s.name}</span><strong>{s.employee_count}</strong></div><progress max={hr.employee_count} value={s.employee_count}/></div>)}</div></section>
          <section className="card"><h2>Кому нужен другой путь</h2><p>Нет доступной активности, закрывающей разрыв. Это не оценка вовлечённости.</p>{hr.no_next_step.map(p=><p key={p.employee_id}><button className="link" onClick={()=>{setSelected(p.employee_id);setTab('profile');}}>{p.full_name}</button> — {p.reason}</p>)}</section>
          <section className="card"><h2>Участие по активностям</h2><div className="table-wrap"><table><thead><tr><th>Активность</th><th>Завершено</th><th>В процессе</th><th>Пропуски / отказы</th></tr></thead><tbody>{hr.participation.map(e=><tr key={e.event_id}><td>{e.title}</td><td>{e.statuses.completed||0}</td><td>{e.statuses.in_progress||0}</td><td>{(e.statuses.no_show||0)+(e.statuses.declined||0)+(e.statuses.dropped||0)}</td></tr>)}</tbody></table></div></section>
        </>}
      </>}
    </main>
  </div>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
