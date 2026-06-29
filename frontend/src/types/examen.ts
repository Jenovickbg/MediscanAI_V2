export interface ExamenMetadata {
  patient_id: string
  study_instance_uid: string
  date_examen: string | null
  nb_coupes: number
  dimensions: number[] | null
  pixel_spacing: number[] | null
  slice_thickness: number | null
  demo?: boolean
}

export interface UploadResponse {
  task_id: string | null
  study_id: string | null
  nb_coupes: number | null
  metadata: ExamenMetadata | null
  preview_slices: number[]
  files_received: number
  total_files: number | null
  finalized: boolean
}

export interface UploadStatus {
  task_id: string
  status: 'pending' | 'running' | 'done' | 'error'
  progress: number
  files_received: number
  total_files: number | null
  error: string | null
  result: UploadResponse | null
}

export interface Examen {
  id: number
  study_instance_uid: string
  patient_id: string
  date_examen: string | null
  nb_coupes: number
  dicom_path: string
  uploaded_at: string
  uploaded_by: number
}

export type ExamenResultFilter = 'all' | 'fracture' | 'normal'
export type ExamenPeriodFilter = 'all' | 'week' | 'month'

export interface ExamenListItem {
  id: number
  study_id: string
  patient_id: string
  date: string
  nb_coupes: number
  uploaded_at: string
  vertebres: string[]
  score_global: number | null
  fracture_detectee: boolean | null
  analysed: boolean
  uploaded_by?: number | null
  medecin_nom?: string | null
}

export interface ExamenListResponse {
  items: ExamenListItem[]
  total: number
  page: number
  limit: number
}

export interface FetchExamensParams {
  page?: number
  limit?: number
  search?: string
  result?: ExamenResultFilter
  period?: ExamenPeriodFilter
}
