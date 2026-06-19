import { Activity, Brain, Target } from 'lucide-react'

import type { RecallMetrics } from '../../types/stats'
import { Card, CardBody, CardHeader } from '../ui'

interface ModelMetricsPanelProps {
  metrics: RecallMetrics
}

const METRIC_CONFIG = [
  { key: 'recall' as const, label: 'Recall', icon: Target },
  { key: 'auc' as const, label: 'AUC', icon: Activity },
  { key: 'f1' as const, label: 'F1-Score', icon: Brain },
]

export function ModelMetricsPanel({ metrics }: ModelMetricsPanelProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <span>Métriques du modèle</span>
        <span className="text-xs font-normal text-text-muted">{metrics.model_name}</span>
      </CardHeader>
      <CardBody>
        <div className="grid gap-4 sm:grid-cols-3">
          {METRIC_CONFIG.map(({ key, label, icon: Icon }) => (
            <div
              key={key}
              className="rounded-lg border border-border bg-bg-elevated px-4 py-4"
            >
              <div className="mb-2 flex items-center gap-2 text-text-muted">
                <Icon className="h-4 w-4 text-accent-cyan" aria-hidden="true" />
                <span className="text-xs uppercase tracking-wide">{label}</span>
              </div>
              <p className="font-mono text-3xl text-text-primary">
                {(metrics[key] * 100).toFixed(1)} %
              </p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-text-muted">
          Métriques de validation sur le jeu de test du modèle entraîné (DenseNet-121 2.5D).
        </p>
      </CardBody>
    </Card>
  )
}
