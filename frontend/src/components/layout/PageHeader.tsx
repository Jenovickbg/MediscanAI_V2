import type { ReactNode } from 'react'

import { useClock } from '../../hooks/useClock'
import { useAuthStore } from '../../store/authStore'

interface PageHeaderProps {
  title?: string
  subtitle?: string
  actions?: ReactNode
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  const user = useAuthStore((s) => s.user)
  const { date, time } = useClock()

  const greeting = user?.nom?.startsWith('Dr')
    ? `Bonjour ${user.nom}`
    : `Bonjour Dr. ${user?.nom ?? 'Utilisateur'}`

  return (
    <header className="border-b border-border bg-bg-secondary/50 px-4 py-5 sm:px-6 lg:px-8 lg:py-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">{title ?? greeting}</h1>
          <p className="mt-1 capitalize text-sm text-text-secondary">{date}</p>
          <p className="font-mono text-xs text-accent-cyan">{time}</p>
          {subtitle && <p className="mt-2 text-sm text-text-secondary">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </header>
  )
}
