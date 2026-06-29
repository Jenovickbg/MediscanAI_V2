import type { AnalyseStartResponse, AnalyseStatus, ResultatAnalyse } from '../types/analyse'
import { apiClient } from './client'

/** Le backend peut être bloqué longtemps pendant l'inférence CPU (GIL). */
const ANALYSE_TIMEOUT_MS = 300_000

export async function startAnalysis(
  studyId: string,
  force = false,
): Promise<AnalyseStartResponse> {
  const { data } = await apiClient.post<AnalyseStartResponse>(`/analyse/${studyId}`, null, {
    params: force ? { force: true } : undefined,
    timeout: ANALYSE_TIMEOUT_MS,
  })
  return data
}

export async function fetchAnalysisStatus(studyId: string): Promise<AnalyseStatus> {
  const { data } = await apiClient.get<AnalyseStatus>(`/analyse/${studyId}/status`, {
    timeout: ANALYSE_TIMEOUT_MS,
  })
  return data
}

export async function fetchAnalysisResults(studyId: string): Promise<ResultatAnalyse> {
  const { data } = await apiClient.get<ResultatAnalyse>(`/analyse/${studyId}/resultats`, {
    timeout: ANALYSE_TIMEOUT_MS,
  })
  return data
}
