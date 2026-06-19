import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { FolderPlus } from 'lucide-react'

import { fetchDashboardStats } from '../api/stats'
import { DashboardStatCards, RecentExamsTable } from '../components/dashboard'
import { PageHeader, PageShell } from '../components/layout'
import { Button, StatCardsSkeleton, TableSkeleton } from '../components/ui'

export function DashboardPage() {
  const navigate = useNavigate()

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: fetchDashboardStats,
    staleTime: 30_000,
  })

  return (
    <>
      <PageHeader
        actions={
          <Button
            icon={<FolderPlus className="h-4 w-4" />}
            onClick={() => navigate('/import')}
          >
            Importer un examen DICOM
          </Button>
        }
      />

      <PageShell>
        {isLoading && (
          <>
            <StatCardsSkeleton />
            <TableSkeleton rows={6} />
          </>
        )}

        {isError && (
          <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
            {error instanceof Error ? error.message : 'Impossible de charger le tableau de bord'}
          </div>
        )}

        {data && (
          <>
            <DashboardStatCards stats={data} />
            <RecentExamsTable exams={data.recent_exams} />
          </>
        )}
      </PageShell>
    </>
  )
}
