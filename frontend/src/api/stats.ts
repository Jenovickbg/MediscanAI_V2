import type { DashboardStats, HistoriqueStats, StatsPeriod } from '../types/stats'
import { apiClient } from './client'

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const { data } = await apiClient.get<DashboardStats>('/stats/dashboard')
  return data
}

export async function fetchHistoriqueStats(period: StatsPeriod = '30d'): Promise<HistoriqueStats> {
  const { data } = await apiClient.get<HistoriqueStats>('/stats/historique', {
    params: { period },
  })
  return data
}
