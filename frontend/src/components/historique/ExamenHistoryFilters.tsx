import { Search } from 'lucide-react'

import type { ExamenPeriodFilter, ExamenResultFilter } from '../../types/examen'
import { cn } from '../../utils/cn'

interface ExamenHistoryFiltersProps {
  search: string
  onSearchChange: (value: string) => void
  resultFilter: ExamenResultFilter
  onResultFilterChange: (value: ExamenResultFilter) => void
  periodFilter: ExamenPeriodFilter
  onPeriodFilterChange: (value: ExamenPeriodFilter) => void
}

const RESULT_FILTERS: { id: ExamenResultFilter; label: string }[] = [
  { id: 'all', label: 'Tous' },
  { id: 'fracture', label: 'Fracture détectée' },
  { id: 'normal', label: 'Normal' },
]

const PERIOD_FILTERS: { id: ExamenPeriodFilter; label: string }[] = [
  { id: 'all', label: 'Toutes dates' },
  { id: 'week', label: 'Cette semaine' },
  { id: 'month', label: 'Ce mois' },
]

function FilterChip({
  active,
  label,
  onClick,
}: {
  active: boolean
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'rounded-lg border px-3 py-1.5 text-xs transition-colors',
        active
          ? 'border-accent-blue bg-accent-blue/15 text-text-primary'
          : 'border-border bg-bg-tertiary text-text-muted hover:border-border-light hover:text-text-secondary',
      )}
    >
      {label}
    </button>
  )
}

export function ExamenHistoryFilters({
  search,
  onSearchChange,
  resultFilter,
  onResultFilterChange,
  periodFilter,
  onPeriodFilterChange,
}: ExamenHistoryFiltersProps) {
  return (
    <div className="space-y-4">
      <div className="relative max-w-md">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted"
          aria-hidden="true"
        />
        <input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Rechercher par Patient ID ou Study UID…"
          className="w-full rounded-lg border border-border bg-bg-tertiary py-2 pl-10 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:border-accent-blue focus:outline-none focus:ring-1 focus:ring-accent-blue"
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-text-muted">Résultat :</span>
        {RESULT_FILTERS.map((filter) => (
          <FilterChip
            key={filter.id}
            active={resultFilter === filter.id}
            label={filter.label}
            onClick={() => onResultFilterChange(filter.id)}
          />
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-text-muted">Période :</span>
        {PERIOD_FILTERS.map((filter) => (
          <FilterChip
            key={filter.id}
            active={periodFilter === filter.id}
            label={filter.label}
            onClick={() => onPeriodFilterChange(filter.id)}
          />
        ))}
      </div>
    </div>
  )
}
