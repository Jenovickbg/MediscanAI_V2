import { useEffect, useState } from 'react'
import { isAxiosError } from 'axios'
import { useQuery } from '@tanstack/react-query'

import { fetchExamensList, useDeleteExamenMutation } from '../api/examens'
import { ExamenHistoryFilters, ExamenHistoryTable } from '../components/historique'
import { PageHeader, PageShell } from '../components/layout'
import { Button, Modal } from '../components/ui'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import type { ExamenListItem, ExamenPeriodFilter, ExamenResultFilter } from '../types/examen'

const PAGE_SIZE = 20

function extractError(err: unknown, fallback: string): string {
  if (isAxiosError(err) && err.response?.data?.detail) {
    const detail = err.response.data.detail
    return typeof detail === 'string' ? detail : fallback
  }
  return fallback
}

export function HistoriquePage() {
  const [search, setSearch] = useState('')
  const [resultFilter, setResultFilter] = useState<ExamenResultFilter>('all')
  const [periodFilter, setPeriodFilter] = useState<ExamenPeriodFilter>('all')
  const [page, setPage] = useState(1)
  const [examToDelete, setExamToDelete] = useState<ExamenListItem | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const deleteMutation = useDeleteExamenMutation()
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

  async function handleConfirmDelete() {
    if (!examToDelete) return
    setDeleteError(null)
    try {
      await deleteMutation.mutateAsync(examToDelete.study_id)
      setExamToDelete(null)
      if (data && data.items.length === 1 && page > 1) {
        setPage(page - 1)
      }
    } catch (err) {
      setDeleteError(extractError(err, 'Impossible de supprimer l\'examen'))
    }
  }

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
          onDelete={setExamToDelete}
          deletingStudyId={deleteMutation.isPending ? examToDelete?.study_id ?? null : null}
        />
      </PageShell>

      <Modal
        open={examToDelete !== null}
        onClose={() => {
          if (!deleteMutation.isPending) {
            setExamToDelete(null)
            setDeleteError(null)
          }
        }}
        title="Supprimer l'examen"
        footer={
          <>
            <Button
              variant="ghost"
              onClick={() => {
                setExamToDelete(null)
                setDeleteError(null)
              }}
              disabled={deleteMutation.isPending}
            >
              Annuler
            </Button>
            <Button
              variant="danger"
              onClick={handleConfirmDelete}
              loading={deleteMutation.isPending}
            >
              Supprimer
            </Button>
          </>
        }
      >
        {deleteError && (
          <p className="mb-3 text-sm text-danger">{deleteError}</p>
        )}
        <p className="text-sm text-text-secondary">
          Voulez-vous supprimer définitivement l&apos;examen du patient{' '}
          <span className="font-mono text-text-primary">{examToDelete?.patient_id}</span>
          {' '}? Les fichiers DICOM, les résultats d&apos;analyse et la reconstruction 3D seront
          effacés. Cette action est irréversible.
        </p>
      </Modal>
    </>
  )
}
