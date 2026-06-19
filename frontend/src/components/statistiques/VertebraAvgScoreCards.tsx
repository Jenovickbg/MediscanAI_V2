import type { VertebraStat } from '../../types/stats'
import { cn } from '../../utils/cn'
import { Card, CardBody, CardHeader } from '../ui'

interface VertebraAvgScoreCardsProps {
  data: VertebraStat[]
}

function scoreColor(avgScore: number): string {
  if (avgScore >= 0.6) return 'text-danger'
  if (avgScore >= 0.3) return 'text-warning'
  return 'text-safe'
}

function scoreBg(avgScore: number): string {
  if (avgScore >= 0.6) return 'border-danger/30 bg-danger/10'
  if (avgScore >= 0.3) return 'border-warning/30 bg-warning/10'
  return 'border-safe/30 bg-safe/5'
}

export function VertebraAvgScoreCards({ data }: VertebraAvgScoreCardsProps) {
  return (
    <Card>
      <CardHeader>Score moyen par vertèbre</CardHeader>
      <CardBody>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          {data.map((item) => {
            const pct = item.avg_score * 100
            return (
              <div
                key={item.vertebre}
                className={cn(
                  'rounded-lg border px-3 py-3 text-center',
                  scoreBg(item.avg_score),
                )}
              >
                <p className="text-xs font-semibold text-text-muted">{item.vertebre}</p>
                <p className={cn('mt-1 font-mono text-lg font-semibold', scoreColor(item.avg_score))}>
                  {pct.toFixed(1)} %
                </p>
                <p className="mt-1 text-[10px] text-text-muted">
                  {item.fracture_count} fracture{item.fracture_count !== 1 ? 's' : ''}
                </p>
              </div>
            )
          })}
        </div>
      </CardBody>
    </Card>
  )
}
