import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { User } from '../types/auth'

interface AuthStore {
  token: string | null
  user: User | null
  isLoading: boolean
  setAuth: (token: string, user: User) => void
  setUser: (user: User) => void
  setLoading: (loading: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isLoading: true,
      setAuth: (token, user) => set({ token, user, isLoading: false }),
      setUser: (user) => set({ user, isLoading: false }),
      setLoading: (isLoading) => set({ isLoading }),
      logout: () => set({ token: null, user: null, isLoading: false }),
    }),
    {
      name: 'mediscanai-auth',
      partialize: (state) => ({ token: state.token, user: state.user }),
      onRehydrateStorage: () => (state) => {
        state?.setLoading(false)
      },
    },
  ),
)

export const selectIsAuthenticated = (state: AuthStore): boolean =>
  state.token !== null && state.user !== null
