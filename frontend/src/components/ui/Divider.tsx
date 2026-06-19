import { cn } from '../../utils/cn'

interface DividerProps {
  className?: string
  label?: string
  orientation?: 'horizontal' | 'vertical'
}

export function Divider({
  className,
  label,
  orientation = 'horizontal',
}: DividerProps) {
  if (orientation === 'vertical') {
    return (
      <div
        role="separator"
        aria-orientation="vertical"
        className={cn('mx-2 w-px self-stretch bg-border', className)}
      />
    )
  }

  if (label) {
    return (
      <div className={cn('flex items-center gap-3', className)}>
        <div className="h-px flex-1 bg-border" />
        <span className="text-xs text-text-muted">{label}</span>
        <div className="h-px flex-1 bg-border" />
      </div>
    )
  }

  return (
    <div
      role="separator"
      aria-orientation="horizontal"
      className={cn('h-px w-full bg-border', className)}
    />
  )
}
