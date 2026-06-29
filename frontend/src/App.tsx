import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'

import { refreshSession, setupApiInterceptors } from './api/client'
import { AdminRoute } from './components/auth/AdminRoute'
import { GuestRoute } from './components/auth/GuestRoute'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { AppLayout } from './components/layout'
import { LoadingSpinner } from './components/ui'
import { DashboardPage } from './pages/DashboardPage'
import { DesignSystemShowcase } from './pages/DesignSystemShowcase'
import { HistoriquePage } from './pages/HistoriquePage'
import { ImportPage } from './pages/ImportPage'
import { LoginPage } from './pages/LoginPage'
import { MedecinsPage } from './pages/MedecinsPage'
import { ParametresPage } from './pages/ParametresPage'
import { ProfilPage } from './pages/ProfilPage'
import { RapportPage } from './pages/RapportPage'
import { StatistiquesPage } from './pages/StatistiquesPage'
import { ViewerPage } from './pages/ViewerPage'
import { useAuthStore } from './store/authStore'

function AppRoutes() {
  const navigate = useNavigate()
  const [bootstrapped, setBootstrapped] = useState(false)

  useEffect(() => {
    setupApiInterceptors(() => navigate('/login', { replace: true }))

    async function bootstrapAuth() {
      const { token, setLoading } = useAuthStore.getState()
      try {
        if (token) {
          await Promise.race([
            refreshSession(),
            new Promise<never>((_, reject) => {
              window.setTimeout(() => reject(new Error('auth-timeout')), 10_000)
            }),
          ])
        } else {
          setLoading(false)
        }
      } catch {
        useAuthStore.getState().setLoading(false)
      } finally {
        setBootstrapped(true)
      }
    }

    if (useAuthStore.persist.hasHydrated()) {
      void bootstrapAuth()
      return
    }

    const unsub = useAuthStore.persist.onFinishHydration(() => {
      void bootstrapAuth()
    })
    return unsub
  }, [navigate])

  if (!bootstrapped) {
    return (
      <div className="flex min-h-full items-center justify-center bg-bg-primary">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      <Route
        path="/login"
        element={
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        }
      />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/historique" element={<HistoriquePage />} />
          <Route path="/statistiques" element={<StatistiquesPage />} />
          <Route path="/parametres" element={<ParametresPage />} />
          <Route path="/profil" element={<ProfilPage />} />
          <Route element={<AdminRoute />}>
            <Route path="/admin/medecins" element={<MedecinsPage />} />
          </Route>
        </Route>

        <Route path="/design-system" element={<DesignSystemShowcase />} />
        <Route path="/viewer/:studyId" element={<ViewerPage />} />
        <Route path="/rapport/:studyId" element={<RapportPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

function App() {
  return <AppRoutes />
}

export default App
