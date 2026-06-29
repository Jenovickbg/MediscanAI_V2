import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Eye, Trash2 } from 'lucide-react'

import { useAuthStore } from '../../store/authStore'
import type { ExamenListItem } from '../../types/examen'
import { Badge, Button, Card, CardBody, CardHeader, LoadingSpinner } from '../ui'

interface ExamenHistoryTableProps {
  exams: ExamenListItem[]
  isLoading?: boolean
  page: number
  total: number
  limit: number
  onPageChange: (page: number) => void
  onDelete?: (exam: ExamenListItem) => void
  deletingStudyId?: string | null
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

export function ExamenHistoryTable({
  exams,
  isLoading,
  page,
  total,
  limit,
  onPageChange,
  onDelete,
  deletingStudyId,
}: ExamenHistoryTableProps) {
  const navigate = useNavigate()
  const isAdmin = useAuthStore((s) => s.user?.role === 'admin')
  const totalPages = Math.max(1, Math.ceil(total / limit))
  const rangeStart = total === 0 ? 0 : (page - 1) * limit + 1
  const rangeEnd = Math.min(page * limit, total)

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <span>Liste des examens</span>
        {!isLoading && (
          <span className="text-xs font-normal text-text-muted">
            {total === 0 ? 'Aucun résultat' : `${rangeStart}–${rangeEnd} sur ${total}`}
          </span>
        )}
      </CardHeader>
      <CardBody className="p-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <LoadingSpinner label="Chargement des examens…" />
          </div>
        ) : exams.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-text-muted">
            Aucun examen ne correspond à vos critères.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-bg-secondary/50 text-xs uppercase tracking-wide text-text-muted">
                  <th className="px-4 py-3 font-medium">Patient ID</th>
                  {isAdmin && <th className="px-4 py-3 font-medium">Médecin</th>}
                  <th className="px-4 py-3 font-medium">Date import</th>
                  <th className="px-4 py-3 font-medium">Coupes</th>
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
                    className="cursor-pointer border-b border-border/60 transition-colors hover:bg-bg-elevated/40"
                    onClick={() => navigate(`/viewer/${exam.study_id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-text-primary">
                      {exam.patient_id}
                    </td>
                    {isAdmin && (
                      <td className="px-4 py-3 text-text-secondary">
                        {exam.medecin_nom ?? '—'}
                      </td>
                    )}
                    <td className="px-4 py-3 text-text-secondary">
                      {formatDate(exam.date)}
                    </td>
                    <td className="px-4 py-3 font-mono text-text-secondary">
                      {exam.nb_coupes}
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
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          className="h-8 px-2 text-xs"
                          icon={<Eye className="h-3.5 w-3.5" />}
                          onClick={(event) => {
                            event.stopPropagation()
                            navigate(`/viewer/${exam.study_id}`)
                          }}
                        >
                          Voir
                        </Button>
                        {onDelete && (
                          <Button
                            variant="ghost"
                            className="h-8 px-2 text-xs text-danger hover:text-danger"
                            aria-label="Supprimer"
                            icon={<Trash2 className="h-3.5 w-3.5" />}
                            loading={deletingStudyId === exam.study_id}
                            onClick={(event) => {
                              event.stopPropagation()
                              onDelete(exam)
                            }}
                          >
                            Supprimer
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-4 py-3">
            <Button
              variant="ghost"
              className="h-8 px-2 text-xs"
              disabled={page <= 1}
              icon={<ChevronLeft className="h-4 w-4" />}
              onClick={() => onPageChange(page - 1)}
            >
              Précédent
            </Button>
            <span className="font-mono text-xs text-text-muted">
              Page {page} / {totalPages}
            </span>
            <Button
              variant="ghost"
              className="h-8 px-2 text-xs"
              disabled={page >= totalPages}
              icon={<ChevronRight className="h-4 w-4" />}
              onClick={() => onPageChange(page + 1)}
            >
              Suivant
            </Button>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
