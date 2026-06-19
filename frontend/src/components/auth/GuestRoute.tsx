import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { selectIsAuthenticated, useAuthStore } from '../../store/authStore'

interface GuestRouteProps {
  children: ReactNode
}

export function GuestRoute({ children }: GuestRouteProps) {
  const isLoading = useAuthStore((s) => s.isLoading)
  const isAuthenticated = useAuthStore(selectIsAuthenticated)

  if (isLoading) {
    return null
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
