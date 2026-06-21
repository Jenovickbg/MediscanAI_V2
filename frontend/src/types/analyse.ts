export type NiveauRisque = 'normal' | 'incertain' | 'eleve'

export interface BoundingBox {
  x: number
  y: number
  w: number
  h: number
}

export interface VertebreResultat {
  probabilite: number
  bounding_box?: BoundingBox | null
  coupe_reference: number
  niveau_risque: NiveauRisque
}

/** Vue aplatie C1–C7 pour les panneaux UI (dérivée de scores_par_vertebre). */
export interface ScoreVertebre {
  vertebre: string
  probabilite: number
  niveau_risque: NiveauRisque
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
  scores_par_vertebre: Record<string, VertebreResultat>
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
