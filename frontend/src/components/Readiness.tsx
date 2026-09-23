import { useEffect, useRef, useState } from 'react'

export default function Readiness({ value }: { value: number }) {
  const [display, setDisplay] = useState(value)
  const previous = useRef(value)
  useEffect(() => {
    const from = previous.current
    previous.current = value
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    let frame: number
    const start = performance.now()
    const animate = (now: number) => {
      const progress = Math.min((now - start) / 800, 1)
      setDisplay(Math.round(from + (value - from) * (1 - (1 - progress) ** 3)))
      if (progress < 1) frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [value])
  return <div className="readiness-ring" role="img" aria-label={`Готовность к цели: ${value}%`}>
    <svg viewBox="0 0 120 120" aria-hidden="true"><circle className="ring-track" cx="60" cy="60" r="51" /><circle className="ring-value" cx="60" cy="60" r="51" pathLength="100" strokeDasharray={`${value} 100`} /></svg>
    <div><strong>{window.matchMedia('(prefers-reduced-motion: reduce)').matches ? value : display}<small>%</small></strong><span>готовность</span></div>
  </div>
}
