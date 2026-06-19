export interface ScoreVertebre {
  vertebre: string
  probabilite: number
  localisation: string
  bounding_box_x: number
  bounding_box_y: number
  bounding_box_w: number
  bounding_box_h: number
  coupe_reference: number
}

export interface ResultatAnalyse {
  study_id: string
  score_global: number
  fracture_detectee: boolean
  scores_vertebres: ScoreVertebre[]
  rapport_clinique: string
  date_analyse: string
  duree_analyse_sec: number
  seuil_utilise: number
  mode_mock: boolean
}

export interface AnalyseStartResponse {
  task_id: string
  study_id: string
}

export interface AnalyseStatus {
  study_id: string
  status: 'pending' | 'running' | 'done' | 'error'
  progress: number
  error: string | null
}
