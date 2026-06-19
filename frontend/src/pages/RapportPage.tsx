import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Download, Printer } from 'lucide-react'

import { fetchAnalysisResults } from '../api/analyse'
import { fetchExamen } from '../api/examens'
import { downloadReportPdf, triggerPdfDownload } from '../api/report'
import { ClinicalReportContent } from '../components/report'
import { Button, LoadingSpinner } from '../components/ui'

export function RapportPage() {
  const { studyId } = useParams<{ studyId: string }>()
  const navigate = useNavigate()
  const [downloading, setDownloading] = useState(false)

  const examenQuery = useQuery({
    queryKey: ['examen', studyId],
    queryFn: () => fetchExamen(studyId!),
    enabled: Boolean(studyId),
  })

  const resultQuery = useQuery({
    queryKey: ['analysis-results', studyId],
    queryFn: () => fetchAnalysisResults(studyId!),
    enabled: Boolean(studyId),
  })

  if (!studyId) return null

  const isLoading = examenQuery.isLoading || resultQuery.isLoading
  const isError = examenQuery.isError || resultQuery.isError
  const examen = examenQuery.data
  const result = resultQuery.data

  async function handleDownloadPdf() {
    if (!studyId) return
    setDownloading(true)
    try {
      const blob = await downloadReportPdf(studyId)
      triggerPdfDownload(blob, studyId)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="rapport-print-root min-h-screen bg-white">
      <div className="no-print sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-white/95 px-6 py-3 backdrop-blur">
        <Button
          variant="ghost"
          className="border-gray-300 text-gray-700 hover:bg-gray-100"
          icon={<ArrowLeft className="h-4 w-4" />}
          onClick={() => navigate(`/viewer/${studyId}`)}
        >
          Retour au viewer
        </Button>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            className="border-gray-300 text-gray-700 hover:bg-gray-100"
            icon={<Printer className="h-4 w-4" />}
            onClick={() => window.print()}
          >
            Imprimer / Exporter PDF
          </Button>
          <Button
            loading={downloading}
            icon={<Download className="h-4 w-4" />}
            onClick={() => void handleDownloadPdf()}
          >
            Télécharger PDF
          </Button>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-24">
          <LoadingSpinner label="Chargement du rapport…" />
        </div>
      )}

      {isError && (
        <div className="mx-auto max-w-2xl px-6 py-12 text-center text-red-600">
          Impossible de charger le rapport. L&apos;analyse doit être terminée.
        </div>
      )}

      {examen && result && <ClinicalReportContent examen={examen} result={result} />}
    </div>
  )
}
