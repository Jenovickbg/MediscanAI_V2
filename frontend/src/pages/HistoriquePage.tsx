import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { fetchExamensList } from '../api/examens'
import { ExamenHistoryFilters, ExamenHistoryTable } from '../components/historique'
import { PageHeader, PageShell } from '../components/layout'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import type { ExamenPeriodFilter, ExamenResultFilter } from '../types/examen'

const PAGE_SIZE = 20

export function HistoriquePage() {
  const [search, setSearch] = useState('')
  const [resultFilter, setResultFilter] = useState<ExamenResultFilter>('all')
  const [periodFilter, setPeriodFilter] = useState<ExamenPeriodFilter>('all')
  const [page, setPage] = useState(1)

  const debouncedSearch = useDebouncedValue(search)

  useEffect(() => {
    setPage(1)
  }, [debouncedSearch, resultFilter, periodFilter])

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['examens-list', page, debouncedSearch, resultFilter, periodFilter],
    queryFn: () =>
      fetchExamensList({
        page,
        limit: PAGE_SIZE,
        search: debouncedSearch || undefined,
        result: resultFilter !== 'all' ? resultFilter : undefined,
        period: periodFilter !== 'all' ? periodFilter : undefined,
      }),
    staleTime: 15_000,
  })

  return (
    <>
      <PageHeader
        title="Historique"
        subtitle="Consultez et recherchez les examens archivés."
      />

      <PageShell>
        <div className="mb-6">
          <ExamenHistoryFilters
            search={search}
            onSearchChange={setSearch}
            resultFilter={resultFilter}
            onResultFilterChange={setResultFilter}
            periodFilter={periodFilter}
            onPeriodFilterChange={setPeriodFilter}
          />
        </div>

        {isError && (
          <div className="mb-4 rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
            {error instanceof Error ? error.message : 'Impossible de charger l\'historique'}
          </div>
        )}

        <ExamenHistoryTable
          exams={data?.items ?? []}
          isLoading={isLoading}
          page={page}
          total={data?.total ?? 0}
          limit={PAGE_SIZE}
          onPageChange={setPage}
        />
      </PageShell>
    </>
  )
}
