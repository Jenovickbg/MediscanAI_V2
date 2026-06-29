import type { ReactNode } from 'react'

import { cn } from '../../utils/cn'

interface PageShellProps {
  children: ReactNode
  className?: string
}

export function PageShell({ children, className }: PageShellProps) {
  return (
    <div className={cn('px-4 py-4 sm:px-6 lg:px-8 lg:py-6', className)}>{children}</div>
  )
}

interface PlaceholderPanelProps {
  title: string
  description: string
}

export function PlaceholderPanel({ title, description }: PlaceholderPanelProps) {
  return (
    <div className="rounded-xl border border-dashed border-border-light bg-bg-tertiary/50 p-8 text-center">
      <h2 className="text-base font-semibold text-text-primary">{title}</h2>
      <p className="mt-2 text-sm text-text-secondary">{description}</p>
    </div>
  )
}
