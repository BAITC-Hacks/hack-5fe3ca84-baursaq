export default function LoadingSkeleton({ label = 'Загружаем профиль и ваш путь развития…' }: { label?: string }) {
  return <div className="skeleton-layout" role="status" aria-label={label}>
    <p className="muted">{label}</p>
    <div className="skeleton skeleton-heading" />
    <div className="skeleton skeleton-profile" />
    <div className="skeleton-columns"><div className="skeleton skeleton-content" /><div className="skeleton skeleton-content" /></div>
  </div>
}
