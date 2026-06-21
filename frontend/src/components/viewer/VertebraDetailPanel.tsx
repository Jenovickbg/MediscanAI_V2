import { motion } from 'framer-motion'
import { Brain, ScanLine } from 'lucide-react'

import type { ScoreVertebre } from '../../types/analyse'
import { useViewerStore } from '../../store/viewerStore'
import {
  generateVertebraExplanation,
  gradCamConfidence,
} from '../../utils/vertebraExplanation'
import { niveauLabel, niveauToRiskLevel } from '../../utils/analyseScores'
import { Badge, ProgressBar } from '../ui'
import { VertebraGradCamThumbnail } from './VertebraGradCamThumbnail'

interface VertebraDetailPanelProps {
  studyId: string
  scores: ScoreVertebre[]
}

function riskBadgeVariant(niveau: ScoreVertebre['niveau_risque']) {
  const level = niveauToRiskLevel(niveau)
  return level === 'high' ? 'danger' : level === 'medium' ? 'warning' : 'success'
}

const VERTEBRA_NAMES: Record<string, string> = {
  C1: '1ère vertèbre cervicale',
  C2: '2ème vertèbre cervicale',
  C3: '3ème vertèbre cervicale',
  C4: '4ème vertèbre cervicale',
  C5: '5ème vertèbre cervicale',
  C6: '6ème vertèbre cervicale',
  C7: '7ème vertèbre cervicale',
}

export function VertebraDetailPanel({ studyId, scores }: VertebraDetailPanelProps) {
  const selectedVertebra = useViewerStore((s) => s.selectedVertebra)

  const score = scores.find((s) => s.vertebre === selectedVertebra)

  if (!selectedVertebra || !score) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-center">
        <p className="text-sm text-text-muted">
          Sélectionnez une vertèbre pour voir le détail
        </p>
      </div>
    )
  }

  const pct = score.probabilite * 100
  const level = niveauToRiskLevel(score.niveau_risque)
  const explanation = generateVertebraExplanation(score)
  const activationScore = gradCamConfidence(score.probabilite)

  return (
    <motion.div
      key={selectedVertebra}
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
      className="space-y-4 p-4"
    >
      <div>
        <h2 className="text-base font-semibold text-text-primary">
          {selectedVertebra} — {VERTEBRA_NAMES[selectedVertebra]}
        </h2>
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
          Score de fracture
        </p>
        <p className="font-mono text-3xl text-text-primary">{pct.toFixed(1)} %</p>
        <ProgressBar value={pct} riskLevel={level} className="mt-2" />
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
          Risque
        </p>
        <Badge variant={riskBadgeVariant(score.niveau_risque)}>
          {niveauLabel(score.niveau_risque)}
        </Badge>
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
          Localisation
        </p>
        <p className="text-sm leading-relaxed text-text-secondary">{score.localisation}</p>
      </div>

      <div>
        <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted">
          <ScanLine className="h-3.5 w-3.5" aria-hidden="true" />
          Coupe de référence
        </p>
        <p className="mb-2 font-mono text-sm text-accent-cyan">
          Coupe {score.coupe_reference + 1}
        </p>
        <VertebraGradCamThumbnail
          studyId={studyId}
          sliceNumber={score.coupe_reference}
          vertebraId={selectedVertebra}
        />
      </div>

      <div>
        <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-text-muted">
          <Brain className="h-3.5 w-3.5" aria-hidden="true" />
          Explication IA
        </p>
        <p className="rounded-lg border border-border bg-bg-tertiary p-3 text-sm leading-relaxed text-text-secondary">
          {explanation}
        </p>
      </div>

      <div>
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
          Confiance Grad-CAM
        </p>
        <p className="font-mono text-lg text-text-primary">
          Score d&apos;activation : {activationScore.toFixed(2)}
        </p>
        <ProgressBar
          value={activationScore * 100}
          riskLevel={level}
          className="mt-2"
        />
      </div>
    </motion.div>
  )
}
