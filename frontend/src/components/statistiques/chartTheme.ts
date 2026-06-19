export const CHART_COLORS = {
  primary: '#378add',
  cyan: '#00c6ff',
  danger: '#ff4757',
  safe: '#00e5a0',
  warning: '#ffa048',
  muted: '#4a5880',
  grid: '#243056',
  text: '#7b8db8',
} as const

export const DONUT_COLORS = [CHART_COLORS.danger, CHART_COLORS.safe] as const

export const VERTEBRA_BAR_COLORS = [
  '#378add',
  '#00c6ff',
  '#00e5a0',
  '#ffa048',
  '#ff4757',
  '#9b59b6',
  '#e67e22',
] as const
