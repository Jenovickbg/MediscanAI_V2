import type { Reconstruction3D } from '../types/reconstruction'
import { apiClient } from './client'

export async function fetchReconstruction3D(studyId: string): Promise<Reconstruction3D> {
  const { data } = await apiClient.get<Reconstruction3D>(
    `/images/${studyId}/reconstruction-3d`,
  )
  return data
}
