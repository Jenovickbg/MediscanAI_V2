import { useCallback, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layers, RotateCcw } from 'lucide-react'

import { fetchCoupeInfo, fetchMprBlob } from '../../api/images'
import { cn } from '../../utils/cn'
import { Button, LoadingSpinner } from '../ui'
import { VIEWER_FRAME_CLASS, VIEWER_IMAGE_CENTER_CLASS } from './viewerLayout'

type MprView = 'sagittal' | 'coronal'

interface MprViewerProps {
  studyId: string
  view: MprView
  className?: string
}

const VIEW_LABELS: Record<MprView, string> = {
  sagittal: 'Sagittale',
  coronal: 'Coronale',
}

function maxIndexForView(view: MprView, info: { nb_coupes: number; width: number; height: number }): number {
  if (view === 'sagittal') return Math.max(info.width - 1, 0)
  return Math.max(info.height - 1, 0)
}

function centralIndexForView(view: MprView, info: { nb_coupes: number; width: number; height: number }): number {
  return Math.floor(maxIndexForView(view, info) / 2)
}

export function MprViewer({ studyId, view, className }: MprViewerProps) {
  const [sliceIndex, setSliceIndex] = useState(0)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [loadingSlice, setLoadingSlice] = useState(true)
  const [viewerError, setViewerError] = useState<string | null>(null)

  const { data: coupeInfo, isLoading: infoLoading, error: infoError } = useQuery({
    queryKey: ['coupe-info', studyId],
    queryFn: () => fetchCoupeInfo(studyId),
  })

  useEffect(() => {
    if (!coupeInfo) return
    setSliceIndex(centralIndexForView(view, coupeInfo))
  }, [coupeInfo, view])

  const loadSlice = useCallback(async () => {
    if (!coupeInfo) return

    setLoadingSlice(true)
    setViewerError(null)

    try {
      const blob = await fetchMprBlob(studyId, view, sliceIndex)
      const url = URL.createObjectURL(blob)
      setImageUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return url
      })
    } catch {
      setViewerError('Impossible de charger cette coupe MPR')
    } finally {
      setLoadingSlice(false)
    }
  }, [coupeInfo, sliceIndex, studyId, view])

  useEffect(() => {
    void loadSlice()
  }, [loadSlice])

  useEffect(() => {
    return () => {
      if (imageUrl) URL.revokeObjectURL(imageUrl)
    }
  }, [imageUrl])

  if (infoLoading) {
    return (
      <div className="flex h-[480px] items-center justify-center rounded-xl border border-border bg-bg-tertiary">
        <LoadingSpinner size="lg" label="Chargement du volume…" />
      </div>
    )
  }

  if (infoError || !coupeInfo) {
    return (
      <div className="flex h-[480px] items-center justify-center rounded-xl border border-border bg-bg-tertiary">
        <p className="text-sm text-danger">Volume indisponible</p>
      </div>
    )
  }

  const maxSlice = maxIndexForView(view, coupeInfo)

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-bg-tertiary px-4 py-3">
        <span className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          Vue {VIEW_LABELS[view]} — MPR
        </span>
      </div>

      <div className="flex gap-3">
        <div className="relative min-w-0 flex-1 overflow-hidden rounded-xl border border-border bg-black">
          <div className={VIEWER_FRAME_CLASS}>
            <div className={VIEWER_IMAGE_CENTER_CLASS}>
              {imageUrl && !loadingSlice && (
                <img
                  src={imageUrl}
                  alt={`Coupe ${VIEW_LABELS[view]} ${sliceIndex + 1}`}
                  className="max-h-full max-w-full object-contain"
                />
              )}

              {loadingSlice && <LoadingSpinner size="md" />}
            </div>
          </div>

          {viewerError && (
            <div className="absolute inset-0 flex items-center justify-center bg-bg-primary/80">
              <p className="text-sm text-danger">{viewerError}</p>
            </div>
          )}

          <div className="pointer-events-none absolute bottom-3 left-3 rounded-lg border border-border bg-bg-primary/90 px-3 py-2 text-xs">
            <p className="font-mono text-accent-cyan">
              {VIEW_LABELS[view]} {sliceIndex + 1} / {maxSlice + 1}
            </p>
          </div>

          <div className="absolute right-3 top-3">
            <Button variant="icon" aria-label="Recharger la coupe" onClick={() => void loadSlice()}>
              <RotateCcw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex w-12 shrink-0 flex-col items-center gap-3 py-2">
          <Layers className="h-4 w-4 text-text-muted" aria-hidden="true" />
          <div className="flex flex-1 items-center justify-center py-4">
            <input
              type="range"
              min={0}
              max={maxSlice}
              value={sliceIndex}
              onChange={(e) => setSliceIndex(Number(e.target.value))}
              style={{ transform: 'rotate(-90deg)', width: 'min(55vh, 420px)' }}
              className={cn(
                'cursor-pointer appearance-none accent-accent-blue',
                'h-2 rounded-full bg-bg-elevated',
              )}
              aria-label={`Navigation ${VIEW_LABELS[view]}`}
            />
          </div>
          <span className="font-mono text-[10px] text-text-muted">{sliceIndex + 1}</span>
        </div>
      </div>
    </div>
  )
}
