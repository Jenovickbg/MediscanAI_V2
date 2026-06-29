import type { NiveauRisque, ResultatAnalyse, ScoreVertebre } from '../types/analyse'
import { VERTEBRAE } from '../store/viewerStore'

const LOCALISATIONS: Record<string, string> = {
  C1: 'Processus odontoïde, arc antérieur',
  C2: 'Corpus vertébral, zone pédiculaire',
  C3: 'Corps vertébral antérieur',
  C4: 'Corps vertébral, plateau supérieur',
  C5: 'Arc vertébral postérieur, Pédicule droit',
  C6: 'Processus articulaire inférieur',
  C7: 'Processus épineux, région cervicale basse',
}

const BBOX_PIXEL_SIZE = 512

export type RiskLevel = 'low' | 'medium' | 'high'

export function niveauToRiskLevel(niveau: NiveauRisque): RiskLevel {
  if (niveau === 'eleve') return 'high'
  if (niveau === 'incertain') return 'medium'
  return 'low'
}

export function niveauLabel(niveau: NiveauRisque): string {
  if (niveau === 'eleve') return 'ÉLEVÉ'
  if (niveau === 'incertain') return 'INCERTAIN'
  return 'NORMAL'
}

export function expandVertebraScores(result: ResultatAnalyse): ScoreVertebre[] {
  return VERTEBRAE.map((vertebre) => {
    const entry = result.scores_par_vertebre[vertebre]
    const bbox = entry?.bounding_box
    return {
      vertebre,
      probabilite: entry?.probabilite ?? 0,
      niveau_risque: entry?.niveau_risque ?? 'normal',
      confiance_vertebre: entry?.confiance_vertebre ?? null,
      localisation: LOCALISATIONS[vertebre] ?? 'Région vertébrale',
      bounding_box_x: bbox ? bbox.x / BBOX_PIXEL_SIZE : 0.35,
      bounding_box_y: bbox ? bbox.y / BBOX_PIXEL_SIZE : 0.25,
      bounding_box_w: bbox ? bbox.w / BBOX_PIXEL_SIZE : 0.18,
      bounding_box_h: bbox ? bbox.h / BBOX_PIXEL_SIZE : 0.22,
      coupe_reference: entry?.coupe_reference ?? 0,
    }
  })
}

export function topDetectedVertebra(result: ResultatAnalyse): ScoreVertebre | null {
  const scores = expandVertebraScores(result)
  const detected = scores.filter((s) => s.niveau_risque !== 'normal' || s.probabilite > 0)
  if (detected.length === 0) return null
  return detected.reduce((max, score) =>
    score.probabilite > max.probabilite ? score : max,
  )
}
