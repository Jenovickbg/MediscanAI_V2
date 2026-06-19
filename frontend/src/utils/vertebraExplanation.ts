import type { ScoreVertebre } from '../types/analyse'

export function gradCamConfidence(probability: number): number {
  return Math.min(0.99, Math.max(0.05, probability * 0.92 + 0.05))
}

export function generateVertebraExplanation(score: ScoreVertebre): string {
  const { vertebre, probabilite, localisation } = score
  const pct = probabilite * 100

  if (probabilite >= 0.6) {
    return (
      `Le modèle a focalisé son attention sur une discontinuité osseuse dans la région ` +
      `${localisation.toLowerCase()} de ${vertebre}. Les zones d'activation Grad-CAM ` +
      `correspondent à un pattern compatible avec une fracture vertébrale (score ${pct.toFixed(1)} %). ` +
      `Une confirmation radiologique est recommandée.`
    )
  }

  if (probabilite >= 0.3) {
    return (
      `Des signaux d'attention modérés ont été détectés au niveau de ${localisation.toLowerCase()} ` +
      `sur ${vertebre} (${pct.toFixed(1)} %). L'activation Grad-CAM est partiellement localisée. ` +
      `Une corrélation clinique est recommandée avant conclusion définitive.`
    )
  }

  return (
    `Le modèle n'a identifié aucun pattern significatif de fracture sur ${vertebre}. ` +
    `L'activation Grad-CAM reste faible et diffuse (${pct.toFixed(1)} %). ` +
    `Aucune anomalie majeure n'est suspectée sur ce segment.`
  )
}
