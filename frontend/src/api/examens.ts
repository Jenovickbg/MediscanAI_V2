import type {
  UploadResponse,
  UploadStatus,
  Examen,
  ExamenListResponse,
  FetchExamensParams,
} from '../types/examen'
import { apiClient } from './client'

const CHUNK_SIZE = 50

function appendFiles(formData: FormData, files: File[]): void {
  for (const file of files) {
    formData.append('files', file, file.webkitRelativePath || file.name)
  }
}

export interface UploadProgressCallback {
  (received: number, total: number): void
}

export async function uploadDicomFiles(
  files: File[],
  patientId: string,
  onProgress?: UploadProgressCallback,
): Promise<UploadResponse> {
  const dicomFiles = files.filter(
    (file) =>
      file.name.toLowerCase().endsWith('.dcm') ||
      file.name.toLowerCase().endsWith('.dicom') ||
      !file.name.includes('.'),
  )

  if (dicomFiles.length === 0) {
    throw new Error('Aucun fichier DICOM (.dcm) sélectionné')
  }

  const total = dicomFiles.length
  let taskId: string | undefined
  let lastResponse: UploadResponse | null = null

  for (let offset = 0; offset < dicomFiles.length; offset += CHUNK_SIZE) {
    const chunk = dicomFiles.slice(offset, offset + CHUNK_SIZE)
    const isLast = offset + chunk.length >= dicomFiles.length
    const needsChunking = total > CHUNK_SIZE

    const formData = new FormData()
    formData.append('patient_id', patientId)
    appendFiles(formData, chunk)

    if (taskId) {
      formData.append('task_id', taskId)
    }
    if (needsChunking) {
      formData.append('total_files', String(total))
    }
    if (needsChunking && isLast) {
      formData.append('finalize', 'true')
    }

    const { data } = await apiClient.post<UploadResponse>('/examens/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    taskId = data.task_id ?? taskId
    onProgress?.(Math.min(offset + chunk.length, total), total)
    lastResponse = data

    if (data.finalized && data.study_id) {
      return data
    }
  }

  if (lastResponse?.finalized && lastResponse.study_id) {
    return lastResponse
  }

  throw new Error("L'upload n'a pas pu être finalisé")
}

export async function fetchUploadStatus(taskId: string): Promise<UploadStatus> {
  const { data } = await apiClient.get<UploadStatus>(`/examens/upload/status/${taskId}`)
  return data
}

export async function loadDemoSample(): Promise<UploadResponse> {
  const { data } = await apiClient.get<UploadResponse>('/demo/load-sample')
  return data
}

export async function fetchExamen(studyId: string): Promise<Examen> {
  const { data } = await apiClient.get<Examen>(`/examens/${studyId}`)
  return data
}

export async function fetchExamensList(
  params: FetchExamensParams = {},
): Promise<ExamenListResponse> {
  const { data } = await apiClient.get<ExamenListResponse>('/examens', { params })
  return data
}

export function getSliceImageUrl(
  studyId: string,
  sliceNumber: number,
): string {
  return `/api/images/${studyId}/coupe/${sliceNumber}?view=axial`
}
