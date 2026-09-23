import type { ReactNode } from 'react'
import { Clock3, Lightbulb, ShieldCheck, Sparkles, Wrench } from 'lucide-react'
import type { RecommendationResponse } from '../api/view'
import './RecommendationDetails.css'

export default function RecommendationDetails({ result, children }: { result: RecommendationResponse; children: ReactNode }) {
  const isAI = result.source === 'llm'
  return <div className="recommendation-results">
    <div className={`source-badge ${isAI ? 'source-ai' : 'source-fallback'}`} role="status">
      {isAI ? <Sparkles size={15} aria-hidden="true" /> : <ShieldCheck size={15} aria-hidden="true" />}
      <span>{isAI ? `AI · ${result.model ?? 'модель не указана'} · ${(result.latency_ms / 1000).toFixed(1)} с` : 'Резервный режим — объяснение от движка'}</span>
    </div>
    {result.summary && <p className="recommendation-summary">{result.summary}</p>}
    {result.trace.length > 0 && <details className="trace-details">
      <summary>Как агент пришёл к решению</summary>
      <ol className="real-trace">
        {result.trace.map((entry, index) => {
          const isTool = entry.step.startsWith('llm→') || entry.step.startsWith('llm->')
          return <li key={`${entry.step}-${index}`} className={isTool ? 'tool-call' : ''}>
            <div className="trace-entry-heading">
              {isTool ? <Wrench size={15} aria-label="Вызов инструмента" /> : <Clock3 size={15} aria-hidden="true" />}
              <strong>{entry.step}</strong>
              <span className="trace-duration">{entry.ms} мс</span>
            </div>
            <p>{entry.detail}</p>
          </li>
        })}
      </ol>
    </details>}
    {children}
    {result.rejected.length > 0 && <section className="rejected-section" aria-label="Почему не другой шаг?">
      <h3><Lightbulb size={18} aria-hidden="true" /> Почему не другой шаг?</h3>
      <ul className="rejected-list">
        {result.rejected.map((item, index) => <li key={`${item.event_id ?? item.skill_id}-${index}`}>
          <strong>{item.title}</strong>
          <p>{item.reason}</p>
        </li>)}
      </ul>
    </section>}
  </div>
}
