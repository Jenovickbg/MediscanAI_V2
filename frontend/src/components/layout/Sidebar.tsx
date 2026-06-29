import { NavLink } from 'react-router-dom'
import { LogOut, Scan } from 'lucide-react'

import { APP_VERSION, getNavItemsForRole } from '../../config/navigation'
import { useAuthStore } from '../../store/authStore'
import { cn } from '../../utils/cn'
import { Badge } from '../ui'
import { StatusIndicator } from './StatusIndicator'

interface SidebarProps {
  onNavigate?: () => void
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)

  const initials = user?.nom
    ?.split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  const navItems = getNavItemsForRole(user?.role)

  return (
    <aside className="flex h-full w-[260px] shrink-0 flex-col border-r border-border bg-bg-secondary">
      <div className="border-b border-border px-4 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-border-light bg-bg-tertiary">
            <Scan className="h-5 w-5 text-accent-cyan" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-text-primary">MediScanAI</p>
            <p className="font-mono text-[10px] text-text-muted">v{APP_VERSION}</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Navigation principale">
        {navItems.map(({ label, path, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                isActive
                  ? 'border border-border-light bg-bg-elevated text-text-primary'
                  : 'text-text-secondary hover:bg-bg-tertiary hover:text-text-primary',
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-3 border-t border-border px-3 py-4">
        <StatusIndicator />

        {user && (
          <div className="rounded-lg border border-border bg-bg-tertiary p-3">
            <div className="flex items-start gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent-blue/20 text-xs font-semibold text-accent-cyan">
                {initials ?? 'MS'}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-text-primary">{user.nom}</p>
                <p className="truncate text-xs text-text-muted">{user.email}</p>
                <Badge variant="info" className="mt-2 capitalize">
                  {user.role}
                </Badge>
              </div>
            </div>
            <button
              type="button"
              onClick={logout}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-text-secondary transition-colors hover:border-border-light hover:bg-bg-elevated hover:text-text-primary"
            >
              <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
              Déconnexion
            </button>
          </div>
        )}
      </div>
    </aside>
  )
}
