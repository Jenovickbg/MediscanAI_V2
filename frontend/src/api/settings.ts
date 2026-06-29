import type { AppSettings, TriageThresholds } from '../types/settings'
import { apiClient } from './client'

function mapHealthPayload(data: Record<string, unknown>): AppSettings {
  const seuils = (data.seuils ?? {}) as Partial<TriageThresholds>
  const modeles = (data.modeles ?? {}) as AppSettings['modeles']

  return {
    version: String(data.version ?? '1.0.0'),
    device: (data.device as string | null) ?? null,
    modeles,
    seuils: {
      seuil_bas: seuils.seuil_bas ?? 0.15,
      seuil_haut: seuils.seuil_haut ?? 0.30,
      score_thresh_rcnn: seuils.score_thresh_rcnn ?? 0.5,
      nms_thresh_rcnn: seuils.nms_thresh_rcnn ?? 0.3,
      max_detections: seuils.max_detections ?? 3,
      derniere_maj: seuils.derniere_maj ?? '2025-06',
      recall_garanti: seuils.recall_garanti,
      auc_modele1: seuils.auc_modele1,
      accuracy_modele3: seuils.accuracy_modele3,
    },
  }
}

/** Charge les paramètres via /health (toujours exposé par le backend). */
export async function fetchAppSettings(): Promise<AppSettings> {
  const { data } = await apiClient.get<Record<string, unknown>>('/health')
  return mapHealthPayload(data)
}

export async function updateTriageThresholds(
  seuils: TriageThresholds,
): Promise<TriageThresholds> {
  const { data } = await apiClient.put<TriageThresholds>('/settings/thresholds', seuils)
  return data
}
