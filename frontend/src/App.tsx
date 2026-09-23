import { useEffect, useState } from 'react'
import { api } from './api/client'

// Placeholder shell — Workstream B replaces this with the Employee / HR screens (see docs/TEAM_PLAN.md).
function App() {
  const [health, setHealth] = useState<string>('checking backend…')

  useEffect(() => {
    api
      .health()
      .then((j) => setHealth(JSON.stringify(j, null, 2)))
      .catch(() => setHealth('backend is not reachable on :8000'))
  }, [])

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-bold">Career Quest</h1>
      <p className="mt-2 text-slate-600">AI-навигатор развития сотрудника · HackAlem AI · Halyk Bank</p>
      <pre className="mt-6 rounded-lg bg-white p-4 text-sm shadow">{health}</pre>
    </main>
  )
}

export default App
