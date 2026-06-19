import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import type { VertebraStat } from '../../types/stats'
import { Card, CardBody, CardHeader } from '../ui'
import { CHART_COLORS, VERTEBRA_BAR_COLORS } from './chartTheme'

interface VertebraFractureChartProps {
  data: VertebraStat[]
}

export function VertebraFractureChart({ data }: VertebraFractureChartProps) {
  const chartData = data.map((item) => ({
    vertebre: item.vertebre,
    count: item.fracture_count,
  }))

  return (
    <Card className="h-full">
      <CardHeader>Fréquence de fracture par vertèbre</CardHeader>
      <CardBody>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} horizontal={false} />
              <XAxis
                type="number"
                allowDecimals={false}
                tick={{ fill: CHART_COLORS.text, fontSize: 11 }}
                axisLine={{ stroke: CHART_COLORS.grid }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="vertebre"
                tick={{ fill: CHART_COLORS.text, fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={36}
              />
              <Tooltip
                contentStyle={{
                  background: '#141d35',
                  border: '1px solid #243056',
                  borderRadius: 8,
                  color: '#e8edf7',
                }}
                formatter={(value) => {
                  const num = typeof value === 'number' ? value : 0
                  return [num, 'Fractures détectées']
                }}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={entry.vertebre}
                    fill={VERTEBRA_BAR_COLORS[index % VERTEBRA_BAR_COLORS.length]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardBody>
    </Card>
  )
}
