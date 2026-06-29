export interface ApiHealth {
  status: string
  model_loaded: boolean
  version: string
  device?: string | null
  modeles?: Record<string, { fichier_present: boolean; charge: boolean; mock: boolean }>
  seuils?: {
    seuil_bas: number
    seuil_haut: number
    score_thresh_rcnn?: number
    nms_thresh_rcnn?: number
    max_detections?: number
    derniere_maj?: string
    recall_garanti?: number
    auc_modele1?: number
    accuracy_modele3?: number
  }
}
