import { useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Circle, ClipboardList, Download } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { downloadReportPdf, triggerPdfDownload } from '../../api/report'
import type { ScoreVertebre } from '../../types/analyse'
import { useViewerStore, type VertebraId } from '../../store/viewerStore'
import { cn } from '../../utils/cn'
import { niveauLabel, niveauToRiskLevel } from '../../utils/analyseScores'
import { Button, ProgressBar } from '../ui'

interface VertebraScorePanelProps {
  studyId: string
  scores: ScoreVertebre[]
  scoreGlobal?: number
  fractureDetectee?: boolean
}

function RiskIcon({ niveau }: { niveau: ScoreVertebre['niveau_risque'] }) {
  const level = niveauToRiskLevel(niveau)
  if (level === 'high') {
    return <AlertTriangle className="h-3 w-3 text-danger" aria-label="Risque élevé" />
  }
  if (level === 'medium') {
    return <AlertTriangle className="h-3 w-3 text-warning" aria-label="Risque incertain" />
  }
  return <Circle className="h-2 w-2 fill-safe text-safe" aria-label="Normal" />
}

export function VertebraScorePanel({
  studyId,
  scores,
  scoreGlobal,
  fractureDetectee,
}: VertebraScorePanelProps) {
  const navigate = useNavigate()
  const [downloading, setDownloading] = useState(false)
  const selectedVertebra = useViewerStore((s) => s.selectedVertebra)
  const setSelectedVertebra = useViewerStore((s) => s.setSelectedVertebra)

  async function handleExportPdf() {
    setDownloading(true)
    try {
      const blob = await downloadReportPdf(studyId)
      triggerPdfDownload(blob, studyId)
    } finally {
      setDownloading(false)
    }
  }

  const orderedScores = [...scores].sort(
    (a, b) =>
      Number(a.vertebre.slice(1)) - Number(b.vertebre.slice(1)),
  )

  return (
    <div className="space-y-3">
      {(scoreGlobal !== undefined || fractureDetectee !== undefined) && (
        <div
          className={cn(
            'rounded-lg border p-3',
            fractureDetectee ? 'border-danger/40 bg-danger/10' : 'border-safe/30 bg-safe/5',
          )}
        >
          <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Résultat global
          </p>
          {fractureDetectee ? (
            <p className="mt-1 text-sm font-medium text-danger">Fracture détectée</p>
          ) : (
            <p className="mt-1 text-sm font-medium text-safe">Normal</p>
          )}
          {scoreGlobal !== undefined && (
            <p className="mt-1 font-mono text-xl text-text-primary">
              {(scoreGlobal * 100).toFixed(1)}%
            </p>
          )}
        </div>
      )}

      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
          Vertèbres
        </p>
        <ul className="space-y-1.5">
          {orderedScores.map((score) => {
            const isSelected = selectedVertebra === score.vertebre
            const pct = score.probabilite * 100
            const riskLevel = niveauToRiskLevel(score.niveau_risque)

            return (
              <li key={score.vertebre}>
                <motion.button
                  type="button"
                  layout
                  onClick={() =>
                    setSelectedVertebra(
                      score.vertebre as VertebraId,
                      score.coupe_reference,
                    )
                  }
                  animate={{
                    scale: isSelected ? 1.02 : 1,
                    borderColor: isSelected ? 'rgba(46, 61, 107, 1)' : 'rgba(36, 48, 86, 1)',
                  }}
                  transition={{ type: 'spring', stiffness: 400, damping: 28 }}
                  className={cn(
                    'w-full rounded-lg border bg-bg-tertiary p-2.5 text-left transition-colors',
                    isSelected && 'bg-bg-elevated ring-1 ring-accent-cyan/30',
                  )}
                >
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <span className="flex items-center gap-2 text-sm font-medium text-text-primary">
                      {score.vertebre}
                      <RiskIcon niveau={score.niveau_risque} />
                    </span>
                    <span className="font-mono text-xs text-text-secondary">
                      {pct.toFixed(0)}%
                    </span>
                  </div>
                  <p className="mb-1.5 text-[10px] uppercase tracking-wide text-text-muted">
                    {niveauLabel(score.niveau_risque)}
                    {score.confiance_vertebre != null && score.niveau_risque !== 'normal' && (
                      <span className="ml-1 normal-case text-text-secondary">
                        · Vertèbre identifiée à {(score.confiance_vertebre * 100).toFixed(0)}%
                      </span>
                    )}
                  </p>
                  <ProgressBar
                    value={pct}
                    riskLevel={riskLevel}
                  />
                </motion.button>
              </li>
            )
          })}
        </ul>
      </div>

      <div className="space-y-2 border-t border-border pt-3">
        <Button
          variant="ghost"
          className="h-9 w-full justify-start text-xs"
          icon={<ClipboardList className="h-3.5 w-3.5" />}
          onClick={() => navigate(`/rapport/${studyId}`)}
        >
          Rapport clinique
        </Button>
        <Button
          variant="ghost"
          className="h-9 w-full justify-start text-xs"
          loading={downloading}
          icon={<Download className="h-3.5 w-3.5" />}
          onClick={() => void handleExportPdf()}
        >
          Exporter PDF
        </Button>
      </div>
    </div>
  )
}
