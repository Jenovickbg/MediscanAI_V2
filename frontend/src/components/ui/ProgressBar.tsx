import { cn } from '../../utils/cn'

type RiskLevel = 'low' | 'medium' | 'high' | 'neutral'

interface ProgressBarProps {
  value: number
  max?: number
  riskLevel?: RiskLevel
  showLabel?: boolean
  className?: string
  label?: string
}

function getRiskLevel(value: number, max: number): RiskLevel {
  const pct = (value / max) * 100
  if (pct < 30) return 'low'
  if (pct < 60) return 'medium'
  return 'high'
}

const fillStyles: Record<RiskLevel, string> = {
  low: 'bg-risk-low',
  medium: 'bg-risk-medium',
  high: 'bg-risk-high',
  neutral: 'bg-accent-blue',
}

export function ProgressBar({
  value,
  max = 100,
  riskLevel,
  showLabel = false,
  className,
  label,
}: ProgressBarProps) {
  const clamped = Math.min(Math.max(value, 0), max)
  const pct = Math.round((clamped / max) * 100)
  const level = riskLevel ?? getRiskLevel(clamped, max)

  return (
    <div className={cn('w-full', className)}>
      {(showLabel || label) && (
        <div className="mb-1 flex items-center justify-between text-xs">
          {label && <span className="text-text-secondary">{label}</span>}
          {showLabel && (
            <span className="font-mono text-text-primary">{pct}%</span>
          )}
        </div>
      )}
      <div
        role="progressbar"
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={max}
        className="h-2 overflow-hidden rounded-full bg-bg-elevated"
      >
        <div
          className={cn('h-full rounded-full transition-all duration-300', fillStyles[level])}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
