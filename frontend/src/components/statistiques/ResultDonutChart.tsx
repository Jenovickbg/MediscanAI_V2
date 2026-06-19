import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import type { ResultDistribution } from '../../types/stats'
import { Card, CardBody, CardHeader } from '../ui'
import { DONUT_COLORS } from './chartTheme'

interface ResultDonutChartProps {
  data: ResultDistribution[]
}

export function ResultDonutChart({ data }: ResultDonutChartProps) {
  const total = data.reduce((sum, item) => sum + item.value, 0)

  return (
    <Card className="h-full">
      <CardHeader>Répartition Fractures vs Normal</CardHeader>
      <CardBody>
        {total === 0 ? (
          <p className="py-16 text-center text-sm text-text-muted">
            Aucune analyse sur cette période.
          </p>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="label"
                  cx="50%"
                  cy="50%"
                  innerRadius={56}
                  outerRadius={88}
                  paddingAngle={3}
                >
                  {data.map((entry, index) => (
                    <Cell
                      key={entry.label}
                      fill={DONUT_COLORS[index % DONUT_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: '#141d35',
                    border: '1px solid #243056',
                    borderRadius: 8,
                    color: '#e8edf7',
                  }}
                  formatter={(value, name) => {
                    const num = typeof value === 'number' ? value : 0
                    return [`${num} (${total > 0 ? ((num / total) * 100).toFixed(1) : '0.0'} %)`, String(name)]
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 flex justify-center gap-6 text-xs">
              {data.map((item, index) => (
                <div key={item.label} className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: DONUT_COLORS[index] }}
                  />
                  <span className="text-text-secondary">
                    {item.label} : <span className="font-mono text-text-primary">{item.value}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
