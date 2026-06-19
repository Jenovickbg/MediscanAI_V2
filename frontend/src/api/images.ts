import { apiClient } from './client'

export interface CoupeInfo {
  nb_coupes: number
  coupe_centrale: number
}

export async function fetchCoupeInfo(studyId: string): Promise<CoupeInfo> {
  const { data } = await apiClient.get<CoupeInfo>(`/images/${studyId}/coupes`)
  return data
}

export async function fetchSliceBlob(
  studyId: string,
  sliceNumber: number,
  view: 'axial' | 'sagittal' | 'coronal' = 'axial',
  windowCenter = 300,
  windowWidth = 1500,
): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(`/images/${studyId}/coupe/${sliceNumber}`, {
    params: {
      view,
      window_center: windowCenter,
      window_width: windowWidth,
    },
    responseType: 'blob',
  })
  return data
}

export async function fetchGradCamBlob(
  studyId: string,
  sliceNumber: number,
  vertebraId?: string,
): Promise<Blob> {
  const { data } = await apiClient.get<Blob>(`/images/${studyId}/gradcam/${sliceNumber}`, {
    params: {
      ...(vertebraId ? { vertebra: vertebraId } : {}),
      overlay: true,
    },
    responseType: 'blob',
  })
  return data
}

export function getSliceImageUrl(
  studyId: string,
  sliceNumber: number,
  view: 'axial' | 'sagittal' | 'coronal' = 'axial',
  windowCenter = 300,
  windowWidth = 1500,
): string {
  const params = new URLSearchParams({
    view,
    window_center: String(windowCenter),
    window_width: String(windowWidth),
  })
  return `/api/images/${studyId}/coupe/${sliceNumber}?${params.toString()}`
}
