import {
  Activity,
  AlertTriangle,
  Clock,
  Scan,
} from 'lucide-react'

import { motion } from 'framer-motion'

import type { DashboardStats } from '../../types/stats'
import { Card, CardBody } from '../ui'

interface DashboardStatCardsProps {
  stats: DashboardStats
}

const STAT_CONFIG = [
  {
    key: 'today_exams' as const,
    label: "Examens analysés aujourd'hui",
    icon: Scan,
    format: (value: number) => String(value),
  },
  {
    key: 'month_fractures' as const,
    label: 'Fractures détectées (ce mois)',
    icon: AlertTriangle,
    format: (value: number) => String(value),
  },
  {
    key: 'avg_score' as const,
    label: 'Taux de détection moyen',
    icon: Activity,
    format: (value: number) => `${(value * 100).toFixed(1)} %`,
  },
  {
    key: 'avg_time' as const,
    label: 'Temps de traitement moyen',
    icon: Clock,
    format: (value: number) => `${value.toFixed(1)} s`,
  },
]

export function DashboardStatCards({ stats }: DashboardStatCardsProps) {
  return (
    <div className="mb-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {STAT_CONFIG.map(({ key, label, icon: Icon, format }, index) => (
        <motion.div
          key={key}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25, delay: index * 0.06 }}
        >
          <Card>
            <CardBody>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs text-text-muted">{label}</p>
                  <p className="mt-2 font-mono text-2xl text-text-primary">
                    {format(stats[key])}
                  </p>
                </div>
                <div className="rounded-lg border border-border bg-bg-elevated p-2">
                  <Icon className="h-4 w-4 text-accent-cyan" aria-hidden="true" />
                </div>
              </div>
            </CardBody>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}
