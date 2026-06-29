export interface ModelStatus {
  fichier_present: boolean
  charge: boolean
  mock: boolean
}

export interface TriageThresholds {
  seuil_bas: number
  seuil_haut: number
  score_thresh_rcnn: number
  nms_thresh_rcnn: number
  max_detections: number
  derniere_maj: string
  recall_garanti?: number | null
  auc_modele1?: number | null
  accuracy_modele3?: number | null
}

export interface AppSettings {
  version: string
  device: string | null
  modeles: Record<string, ModelStatus>
  seuils: TriageThresholds
}

export type WindowPresetId = 'bone' | 'brain' | 'lung' | 'soft' | 'custom'

export interface WindowPreset {
  id: WindowPresetId
  label: string
  windowCenter: number
  windowWidth: number
  description: string
}

export const WINDOW_PRESETS: WindowPreset[] = [
  {
    id: 'bone',
    label: 'Os',
    windowCenter: 300,
    windowWidth: 1500,
    description: 'Fenêtrage osseux standard (défaut MediScanAI)',
  },
  {
    id: 'brain',
    label: 'Cerveau',
    windowCenter: 40,
    windowWidth: 80,
    description: 'Parenchyme cérébral',
  },
  {
    id: 'lung',
    label: 'Poumon',
    windowCenter: -600,
    windowWidth: 1500,
    description: 'Parenchyme pulmonaire',
  },
  {
    id: 'soft',
    label: 'Tissus mous',
    windowCenter: 50,
    windowWidth: 400,
    description: 'Muscle et tissus mous',
  },
]
