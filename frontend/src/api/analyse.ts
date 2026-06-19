import type { AnalyseStartResponse, AnalyseStatus, ResultatAnalyse } from '../types/analyse'
import { apiClient } from './client'

export async function startAnalysis(studyId: string): Promise<AnalyseStartResponse> {
  const { data } = await apiClient.post<AnalyseStartResponse>(`/analyse/${studyId}`)
  return data
}

export async function fetchAnalysisStatus(studyId: string): Promise<AnalyseStatus> {
  const { data } = await apiClient.get<AnalyseStatus>(`/analyse/${studyId}/status`)
  return data
}

export async function fetchAnalysisResults(studyId: string): Promise<ResultatAnalyse> {
  const { data } = await apiClient.get<ResultatAnalyse>(`/analyse/${studyId}/resultats`)
  return data
}
