import { useState, type FormEvent } from 'react'
import { Eye, EyeOff, Scan } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { loginApi } from '../api/auth'
import { Button } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { cn } from '../utils/cn'

export function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await loginApi({ email, password })
      setAuth(response.access_token, response.user)
      navigate('/dashboard', { replace: true })
    } catch {
      setError('Email ou mot de passe incorrect')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className={cn(
        'flex min-h-full items-center justify-center px-4',
        'bg-[radial-gradient(ellipse_at_center,#141D35_0%,#0A0F1E_70%)]',
      )}
    >
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-border-light bg-bg-tertiary">
            <Scan className="h-7 w-7 text-accent-cyan" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-semibold text-text-primary">MediScanAI</h1>
          <p className="mt-2 text-sm text-text-secondary">
            Système Intelligent d&apos;Aide au Diagnostic Orthopédique
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-border bg-bg-tertiary/80 p-6 shadow-xl backdrop-blur-sm"
        >
          <div className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1.5 block text-xs text-text-secondary">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={cn(
                  'w-full rounded-lg border border-border bg-bg-secondary px-3 py-2.5',
                  'text-sm text-text-primary placeholder:text-text-muted',
                  'focus:border-border-light focus:outline-none focus:ring-2 focus:ring-accent-cyan/30',
                )}
                placeholder="admin@mediscanai.cd"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-1.5 block text-xs text-text-secondary">
                Mot de passe
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={cn(
                    'w-full rounded-lg border border-border bg-bg-secondary px-3 py-2.5 pr-10',
                    'text-sm text-text-primary placeholder:text-text-muted',
                    'focus:border-border-light focus:outline-none focus:ring-2 focus:ring-accent-cyan/30',
                  )}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-text-muted hover:text-text-primary"
                  aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {error && (
              <p role="alert" className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
                {error}
              </p>
            )}

            <Button type="submit" loading={loading} className="w-full">
              Se connecter
            </Button>
          </div>
        </form>

        <p className="mt-6 text-center text-xs text-text-muted">
          Comptes de démonstration disponibles après initialisation du serveur.
        </p>
      </div>
    </div>
  )
}
