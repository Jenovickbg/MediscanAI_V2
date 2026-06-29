import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'

import { useAuthStore } from '../store/authStore'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

let interceptorsConfigured = false

export function setupApiInterceptors(onUnauthorized: () => void): void {
  if (interceptorsConfigured) return
  interceptorsConfigured = true

  apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  apiClient.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      const requestUrl = error.config?.url ?? ''
      const isAuthRequest =
        requestUrl.includes('/auth/login') || requestUrl.includes('/auth/me')

      if (error.response?.status === 401 && !isAuthRequest) {
        useAuthStore.getState().logout()
        onUnauthorized()
      }

      return Promise.reject(error)
    },
  )
}

export async function refreshSession(): Promise<boolean> {
  const { token, setUser, logout, setLoading } = useAuthStore.getState()

  if (!token) {
    setLoading(false)
    return false
  }

  try {
    const { data } = await apiClient.get('/auth/me')
    setUser(data)
    return true
  } catch {
    logout()
    return false
  } finally {
    setLoading(false)
  }
}
