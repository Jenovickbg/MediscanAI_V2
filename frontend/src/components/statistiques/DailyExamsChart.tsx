import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { DailyCount } from '../../types/stats'
import { Card, CardBody, CardHeader } from '../ui'
import { CHART_COLORS } from './chartTheme'

interface DailyExamsChartProps {
  data: DailyCount[]
}

function formatDay(iso: string): string {
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: 'short' }).format(
    new Date(iso),
  )
}

export function DailyExamsChart({ data }: DailyExamsChartProps) {
  const chartData = data.map((item) => ({
    ...item,
    label: formatDay(item.date),
  }))

  return (
    <Card className="h-full">
      <CardHeader>Examens analysés par jour</CardHeader>
      <CardBody>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
              <XAxis
                dataKey="label"
                tick={{ fill: CHART_COLORS.text, fontSize: 11 }}
                axisLine={{ stroke: CHART_COLORS.grid }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: CHART_COLORS.text, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: '#141d35',
                  border: '1px solid #243056',
                  borderRadius: 8,
                  color: '#e8edf7',
                }}
                labelFormatter={(_, payload) => {
                  const entry = payload?.[0]?.payload as { date?: string } | undefined
                  return entry?.date
                    ? new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium' }).format(
                        new Date(entry.date),
                      )
                    : ''
                }}
              />
              <Bar dataKey="count" fill={CHART_COLORS.primary} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardBody>
    </Card>
  )
}
