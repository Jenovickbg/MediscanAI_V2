import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, Scan } from 'lucide-react'

import {
  AxialViewer,
  SpineViewer3D,
  VertebraDetailPanel,
  VertebraScorePanel,
} from '../components/viewer'
import { useAnalysis } from '../hooks/useAnalysis'
import { useViewerStore, type VertebraId } from '../store/viewerStore'
import {
  Badge,
  Button,
  LoadingSpinner,
  ProgressBar,
} from '../components/ui'
import { cn } from '../utils/cn'

type ViewerTab = 'axial' | '3d'
type MobilePanel = 'scores' | 'viewer' | 'detail'

export function ViewerPage() {
  const { studyId } = useParams<{ studyId: string }>()
  const { progress, result, error, isRunning, retry } = useAnalysis(studyId)
  const [activeTab, setActiveTab] = useState<ViewerTab>('axial')
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>('viewer')
  const resetViewer = useViewerStore((s) => s.reset)
  const setSelectedVertebra = useViewerStore((s) => s.setSelectedVertebra)

  useEffect(() => {
    return () => resetViewer()
  }, [resetViewer])

  useEffect(() => {
    if (!result || result.scores_vertebres.length === 0) return

    const topScore = result.scores_vertebres.reduce((max, score) =>
      score.probabilite > max.probabilite ? score : max,
    )
    setSelectedVertebra(topScore.vertebre as VertebraId, topScore.coupe_reference)
  }, [result, setSelectedVertebra])

  if (!studyId) return null

  const tabs: { id: ViewerTab; label: string }[] = [
    { id: 'axial', label: 'Axiale' },
    { id: '3d', label: '3D' },
  ]

  const mobilePanels: { id: MobilePanel; label: string; disabled?: boolean }[] = [
    { id: 'scores', label: 'Scores', disabled: !result },
    { id: 'viewer', label: 'Viewer' },
    { id: 'detail', label: 'Détail', disabled: !result },
  ]

  return (
    <div className="flex h-screen flex-col bg-bg-primary">
      <header className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Scan className="h-5 w-5 shrink-0 text-accent-cyan" aria-hidden="true" />
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-text-primary">MediScanAI Viewer</h1>
            <p className="truncate font-mono text-[10px] text-text-muted">{studyId}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {result && (
            <div className="hidden items-center gap-2 sm:flex">
              {result.fracture_detectee ? (
                <Badge variant="danger">
                  <AlertTriangle className="mr-1 h-3 w-3" />
                  Fracture {(result.score_global * 100).toFixed(1)}%
                </Badge>
              ) : (
                <Badge variant="success">
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  Normal
                </Badge>
              )}
              {result.mode_mock && <Badge variant="warning">Mock</Badge>}
            </div>
          )}

          <Button variant="ghost" className="h-8 px-2 text-xs" onClick={() => window.history.back()}>
            Retour
          </Button>
        </div>
      </header>

      {isRunning && (
        <div className="shrink-0 border-b border-border bg-bg-secondary px-4 py-2">
          <div className="flex items-center gap-3">
            <LoadingSpinner size="sm" />
            <span className="text-xs text-text-secondary">Analyse IA — {progress}%</span>
            <div className="flex-1">
              <ProgressBar value={progress} riskLevel="neutral" />
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="shrink-0 border-b border-danger/30 bg-danger/10 px-4 py-2 text-sm text-danger">
          {error}
          <Button variant="ghost" className="ml-2 h-7 px-2 text-xs" onClick={retry}>
            Réessayer
          </Button>
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside className="hidden w-[280px] shrink-0 overflow-y-auto border-r border-border bg-bg-secondary lg:block">
          <div className="border-b border-border p-4">
            <p className="text-xs text-text-muted">Examen</p>
            <p className="font-mono text-sm text-text-primary">{studyId}</p>
          </div>

          <div className="p-4">
            {!result && !isRunning && (
              <p className="text-sm text-text-secondary">En attente de l&apos;analyse…</p>
            )}

            {result && (
              <VertebraScorePanel
                studyId={studyId}
                scores={result.scores_vertebres}
                scoreGlobal={result.score_global}
                fractureDetectee={result.fracture_detectee}
              />
            )}
          </div>
        </aside>

        <main
          className={cn(
            'min-w-0 flex-1 overflow-y-auto p-3 sm:p-4',
            mobilePanel !== 'viewer' && 'hidden lg:block',
          )}
        >
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'rounded-lg border px-3 py-1.5 text-xs transition-colors',
                  activeTab === tab.id
                    ? 'border-border-light bg-bg-elevated text-text-primary'
                    : 'border-border bg-bg-tertiary text-text-muted hover:text-text-secondary',
                )}
              >
                {tab.label}
              </button>
            ))}
            <span className="hidden text-xs text-text-muted xl:inline">
              Sagittale / Coronale / MPR — à venir
            </span>
          </div>

          {activeTab === 'axial' && <AxialViewer studyId={studyId} />}
          {activeTab === '3d' && <SpineViewer3D studyId={studyId} />}
        </main>

        <aside
          className={cn(
            'hidden w-[300px] shrink-0 overflow-y-auto border-l border-border bg-bg-secondary xl:block',
          )}
        >
          <div className="border-b border-border px-4 py-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
              Détail vertèbre
            </h2>
          </div>
          {result ? (
            <VertebraDetailPanel studyId={studyId} scores={result.scores_vertebres} />
          ) : (
            <p className="p-4 text-sm text-text-secondary">Analyse requise</p>
          )}
        </aside>

        {/* Panneaux mobile */}
        <div
          className={cn(
            'min-h-0 flex-1 overflow-y-auto border-t border-border bg-bg-secondary p-3 lg:hidden',
            mobilePanel === 'scores' ? 'block' : 'hidden',
          )}
        >
          {result ? (
            <VertebraScorePanel
              studyId={studyId}
              scores={result.scores_vertebres}
              scoreGlobal={result.score_global}
              fractureDetectee={result.fracture_detectee}
            />
          ) : (
            <p className="text-sm text-text-secondary">En attente de l&apos;analyse…</p>
          )}
        </div>

        <div
          className={cn(
            'min-h-0 flex-1 overflow-y-auto border-t border-border bg-bg-secondary lg:hidden',
            mobilePanel === 'detail' ? 'block' : 'hidden',
          )}
        >
          {result ? (
            <VertebraDetailPanel studyId={studyId} scores={result.scores_vertebres} />
          ) : (
            <p className="p-4 text-sm text-text-secondary">Analyse requise</p>
          )}
        </div>
      </div>

      <nav className="flex shrink-0 border-t border-border bg-bg-secondary lg:hidden">
        {mobilePanels.map((panel) => (
          <button
            key={panel.id}
            type="button"
            disabled={panel.disabled}
            onClick={() => setMobilePanel(panel.id)}
            className={cn(
              'flex-1 py-3 text-xs font-medium transition-colors',
              mobilePanel === panel.id
                ? 'border-t-2 border-accent-cyan text-text-primary'
                : 'text-text-muted',
              panel.disabled && 'opacity-40',
            )}
          >
            {panel.label}
          </button>
        ))}
      </nav>
    </div>
  )
}
