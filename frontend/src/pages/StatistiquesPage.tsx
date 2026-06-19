import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { fetchHistoriqueStats } from '../api/stats'
import { PageHeader, PageShell } from '../components/layout'
import {
  DailyExamsChart,
  ModelMetricsPanel,
  ResultDonutChart,
  VertebraAvgScoreCards,
  VertebraFractureChart,
} from '../components/statistiques'
import { LoadingSpinner } from '../components/ui'
import { cn } from '../utils/cn'
import type { StatsPeriod } from '../types/stats'

const PERIOD_OPTIONS: { id: StatsPeriod; label: string }[] = [
  { id: '7d', label: '7 jours' },
  { id: '30d', label: '30 jours' },
  { id: '90d', label: '90 jours' },
]

export function StatistiquesPage() {
  const [period, setPeriod] = useState<StatsPeriod>('30d')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['historique-stats', period],
    queryFn: () => fetchHistoriqueStats(period),
    staleTime: 30_000,
  })

  return (
    <>
      <PageHeader
        title="Statistiques"
        subtitle="Analyses et métriques du modèle IA."
        actions={
          <div className="flex items-center gap-2">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setPeriod(option.id)}
                className={cn(
                  'rounded-lg border px-3 py-1.5 text-xs transition-colors',
                  period === option.id
                    ? 'border-accent-blue bg-accent-blue/15 text-text-primary'
                    : 'border-border bg-bg-tertiary text-text-muted hover:text-text-secondary',
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        }
      />

      <PageShell>
        {isLoading && (
          <div className="flex items-center justify-center py-16">
            <LoadingSpinner label="Chargement des statistiques…" />
          </div>
        )}

        {isError && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
            {error instanceof Error ? error.message : 'Impossible de charger les statistiques'}
          </div>
        )}

        {data && (
          <div className="space-y-6">
            <div className="grid gap-6 xl:grid-cols-2">
              <DailyExamsChart data={data.daily_counts} />
              <ResultDonutChart data={data.result_distribution} />
            </div>

            <VertebraFractureChart data={data.vertebrae_distribution} />
            <VertebraAvgScoreCards data={data.vertebrae_distribution} />
            <ModelMetricsPanel metrics={data.recall_metrics} />
          </div>
        )}
      </PageShell>
    </>
  )
}
