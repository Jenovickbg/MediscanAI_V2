import type { ApiHealth } from '../types/api'
import { apiClient } from './client'

export async function fetchHealth(): Promise<ApiHealth> {
  const { data } = await apiClient.get<ApiHealth>('/health')
  return data
}
