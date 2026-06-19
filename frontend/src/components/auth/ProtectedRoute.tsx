import { Navigate, Outlet } from 'react-router-dom'

import { LoadingSpinner } from '../ui'
import { selectIsAuthenticated, useAuthStore } from '../../store/authStore'

export function ProtectedRoute() {
  const token = useAuthStore((s) => s.token)
  const isLoading = useAuthStore((s) => s.isLoading)
  const isAuthenticated = useAuthStore(selectIsAuthenticated)

  if (isLoading) {
    return (
      <div className="flex min-h-full items-center justify-center bg-bg-primary">
        <LoadingSpinner size="lg" label="Vérification de la session…" />
      </div>
    )
  }

  if (!token || !isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
