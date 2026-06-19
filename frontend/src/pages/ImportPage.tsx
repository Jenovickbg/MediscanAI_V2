import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Scan } from 'lucide-react'

import { ImportPreviewSlice } from '../components/import/ImportPreviewSlice'
import { DicomUploadZone } from '../components/import/DicomUploadZone'
import { PageHeader, PageShell } from '../components/layout'
import { Badge, Button, Card, CardBody, CardHeader } from '../components/ui'
import type { UploadResponse } from '../types/examen'

export function ImportPage() {
  const navigate = useNavigate()
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null)

  const metadata = uploadResult?.metadata

  return (
    <>
      <PageHeader
        title="Nouvel examen"
        subtitle="Importez un dossier DICOM pour lancer l'analyse IA."
      />

      <PageShell>
        {!uploadResult?.finalized ? (
          <DicomUploadZone onUploadComplete={setUploadResult} />
        ) : (
          <div className="space-y-6">
            <Card>
              <CardHeader className="flex items-center justify-between">
                <span>Examen importé avec succès</span>
                {metadata?.demo && <Badge variant="info">Démo</Badge>}
              </CardHeader>
              <CardBody>
                <dl className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <dt className="text-xs text-text-muted">Patient ID</dt>
                    <dd className="font-mono text-sm text-text-primary">
                      {metadata?.patient_id}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-text-muted">Date examen</dt>
                    <dd className="text-sm text-text-primary">
                      {metadata?.date_examen
                        ? new Date(metadata.date_examen).toLocaleString('fr-FR')
                        : '—'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-text-muted">Nombre de coupes</dt>
                    <dd className="font-mono text-sm text-text-primary">
                      {metadata?.nb_coupes ?? uploadResult.nb_coupes}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-text-muted">Dimensions</dt>
                    <dd className="font-mono text-sm text-text-primary">
                      {metadata?.dimensions?.join(' × ') ?? '—'}
                    </dd>
                  </div>
                </dl>
              </CardBody>
            </Card>

            {uploadResult.study_id && uploadResult.preview_slices.length > 0 && (
              <div>
                <h2 className="mb-3 text-base font-semibold text-text-primary">
                  Aperçu des coupes axiales
                </h2>
                <div className="grid gap-4 sm:grid-cols-3">
                  {uploadResult.preview_slices.map((sliceNum) => (
                    <div
                      key={sliceNum}
                      className="overflow-hidden rounded-xl border border-border bg-bg-tertiary"
                    >
                      <ImportPreviewSlice
                        studyId={uploadResult.study_id!}
                        sliceNumber={sliceNum}
                      />
                      <p className="border-t border-border px-3 py-2 text-center font-mono text-xs text-text-muted">
                        Coupe {sliceNum + 1}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <Button
                icon={<Scan className="h-4 w-4" />}
                onClick={() => navigate(`/viewer/${uploadResult.study_id}`)}
              >
                Analyser cet examen
              </Button>
              <Button variant="ghost" onClick={() => setUploadResult(null)}>
                Importer un autre examen
              </Button>
            </div>
          </div>
        )}
      </PageShell>
    </>
  )
}
