import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { FlaskConical, Upload } from 'lucide-react'

import { loadDemoSample, uploadDicomFiles } from '../../api/examens'
import type { UploadResponse } from '../../types/examen'
import { cn } from '../../utils/cn'
import { Button, ProgressBar } from '../ui'

interface DicomUploadZoneProps {
  onUploadComplete: (result: UploadResponse) => void
}

export function DicomUploadZone({ onUploadComplete }: DicomUploadZoneProps) {
  const [patientId, setPatientId] = useState('')
  const [uploading, setUploading] = useState(false)
  const [demoLoading, setDemoLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState({ current: 0, total: 0 })

  const handleUpload = useCallback(
    async (files: File[]) => {
      if (!patientId.trim()) {
        setError('Veuillez saisir un Patient ID avant l\'import')
        return
      }

      setError(null)
      setUploading(true)
      setProgress({ current: 0, total: files.length })

      try {
        const result = await uploadDicomFiles(files, patientId.trim(), (current, total) => {
          setProgress({ current, total })
        })
        onUploadComplete(result)
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Erreur lors de l\'upload'
        setError(message)
      } finally {
        setUploading(false)
      }
    },
    [onUploadComplete, patientId],
  )

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        void handleUpload(acceptedFiles)
      }
    },
    [handleUpload],
  )

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    noClick: uploading,
    noKeyboard: uploading,
    disabled: uploading,
    multiple: true,
  })

  async function handleDemoLoad() {
    setError(null)
    setDemoLoading(true)
    try {
      const result = await loadDemoSample()
      setPatientId(result.metadata?.patient_id ?? 'DEMO-001')
      onUploadComplete(result)
    } catch {
      setError('Impossible de charger l\'examen de démonstration')
    } finally {
      setDemoLoading(false)
    }
  }

  const progressPct =
    progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="patient-id" className="mb-1.5 block text-xs text-text-secondary">
          Patient ID
        </label>
        <input
          id="patient-id"
          type="text"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          placeholder="Ex. PAT-2025-0042"
          disabled={uploading}
          className={cn(
            'w-full max-w-md rounded-lg border border-border bg-bg-secondary px-3 py-2.5',
            'text-sm text-text-primary placeholder:text-text-muted',
            'focus:border-border-light focus:outline-none focus:ring-2 focus:ring-accent-cyan/30',
          )}
        />
      </div>

      <div
        {...getRootProps()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-14 transition-colors',
          isDragActive
            ? 'border-accent-cyan bg-accent-cyan/5'
            : 'border-border-light bg-bg-tertiary/40 hover:border-accent-blue hover:bg-bg-tertiary',
          uploading && 'pointer-events-none opacity-70',
        )}
      >
        <input
          {...getInputProps({
            // Permet la sélection d'un dossier entier (Chrome / Edge)
            // @ts-expect-error attribut non standard
            webkitdirectory: '',
            directory: '',
          })}
        />
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-bg-elevated">
          <Upload className="h-7 w-7 text-accent-cyan" aria-hidden="true" />
        </div>
        <p className="text-sm font-medium text-text-primary">
          Glissez vos fichiers DICOM ici ou cliquez pour parcourir
        </p>
        <p className="mt-2 text-xs text-text-muted">
          Formats acceptés : .dcm | Tout un dossier d&apos;examen
        </p>
        {!uploading && (
          <Button type="button" variant="ghost" className="mt-4" onClick={open}>
            Parcourir les fichiers
          </Button>
        )}
      </div>

      {uploading && (
        <div className="rounded-xl border border-border bg-bg-tertiary p-4">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="text-text-secondary">Upload en cours…</span>
            <span className="font-mono text-accent-cyan">
              {progress.current} / {progress.total} fichiers
            </span>
          </div>
          <ProgressBar value={progressPct} riskLevel="neutral" />
        </div>
      )}

      {error && (
        <p role="alert" className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-border" />
        <span className="text-xs text-text-muted">ou</span>
        <div className="h-px flex-1 bg-border" />
      </div>

      <Button
        variant="ghost"
        loading={demoLoading}
        icon={<FlaskConical className="h-4 w-4" />}
        onClick={() => void handleDemoLoad()}
        disabled={uploading}
      >
        Charger un examen de démonstration
      </Button>
    </div>
  )
}
