import { useNavigate } from 'react-router-dom'
import { Eye } from 'lucide-react'

import type { RecentExamen } from '../../types/stats'
import { Badge, Button, Card, CardBody, CardHeader, LoadingSpinner } from '../ui'

interface RecentExamsTableProps {
  exams: RecentExamen[]
  isLoading?: boolean
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

function formatVertebres(vertebres: string[]): string {
  if (vertebres.length === 0) return '—'
  return vertebres.join(', ')
}

export function RecentExamsTable({ exams, isLoading }: RecentExamsTableProps) {
  const navigate = useNavigate()

  return (
    <Card>
      <CardHeader>Examens récents</CardHeader>
      <CardBody className="p-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner label="Chargement des examens…" />
          </div>
        ) : exams.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-text-muted">
            Aucun examen importé pour le moment.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-bg-secondary/50 text-xs uppercase tracking-wide text-text-muted">
                  <th className="px-4 py-3 font-medium">Patient ID</th>
                  <th className="px-4 py-3 font-medium">Date import</th>
                  <th className="px-4 py-3 font-medium">Vertèbres</th>
                  <th className="px-4 py-3 font-medium">Score</th>
                  <th className="px-4 py-3 font-medium">Résultat</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {exams.map((exam) => (
                  <tr
                    key={exam.study_id}
                    className="border-b border-border/60 transition-colors hover:bg-bg-elevated/40"
                  >
                    <td className="px-4 py-3 font-mono text-text-primary">
                      {exam.patient_id}
                    </td>
                    <td className="px-4 py-3 text-text-secondary">
                      {formatDate(exam.date)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {formatVertebres(exam.vertebres)}
                    </td>
                    <td className="px-4 py-3 font-mono text-text-primary">
                      {exam.score_global !== null
                        ? `${(exam.score_global * 100).toFixed(1)} %`
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {!exam.analysed ? (
                        <Badge variant="neutral">En attente</Badge>
                      ) : exam.fracture_detectee ? (
                        <Badge variant="danger">Fracture</Badge>
                      ) : (
                        <Badge variant="success">Normal</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        className="h-8 px-2 text-xs"
                        icon={<Eye className="h-3.5 w-3.5" />}
                        onClick={() => navigate(`/viewer/${exam.study_id}`)}
                      >
                        Voir
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
