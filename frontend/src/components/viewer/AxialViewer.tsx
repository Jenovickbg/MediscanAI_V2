import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layers, RotateCcw } from 'lucide-react'

import { fetchCoupeInfo, fetchSliceBlob } from '../../api/images'
import {
  activateViewerTools,
  cornerstone,
  initCornerstone,
  loadPngBlobAsCornerstoneImage,
} from '../../lib/cornerstone'
import { useViewerStore } from '../../store/viewerStore'
import { useSettingsStore } from '../../store/settingsStore'
import { cn } from '../../utils/cn'
import { Button, LoadingSpinner, Slider } from '../ui'
import { GradCamOverlay } from './GradCamOverlay'
import { GradCamToggle } from './GradCamToggle'
import { VIEWER_FRAME_CLASS, VIEWER_INNER_CLASS } from './viewerLayout'

interface AxialViewerProps {
  studyId: string
  className?: string
}

export function AxialViewer({ studyId, className }: AxialViewerProps) {
  const elementRef = useRef<HTMLDivElement>(null)
  const [sliceIndex, setSliceIndex] = useState(0)
  const [loadingSlice, setLoadingSlice] = useState(true)
  const [viewerError, setViewerError] = useState<string | null>(null)
  const [gradCamActive, setGradCamActive] = useState(false)
  const defaultGradCamOpacity = useSettingsStore((s) => s.gradCamOpacity)
  const [gradCamOpacity, setGradCamOpacity] = useState(defaultGradCamOpacity)
  const windowCenter = useSettingsStore((s) => s.windowCenter)
  const windowWidth = useSettingsStore((s) => s.windowWidth)
  const toolsReadyRef = useRef(false)
  const selectedVertebra = useViewerStore((s) => s.selectedVertebra)
  const targetSliceIndex = useViewerStore((s) => s.targetSliceIndex)
  const clearTargetSlice = useViewerStore((s) => s.clearTargetSlice)

  const { data: coupeInfo, isLoading: infoLoading, error: infoError } = useQuery({
    queryKey: ['coupe-info', studyId],
    queryFn: () => fetchCoupeInfo(studyId),
  })

  useEffect(() => {
    if (coupeInfo?.coupe_centrale !== undefined && targetSliceIndex === null) {
      setSliceIndex(coupeInfo.coupe_centrale)
    }
  }, [coupeInfo?.coupe_centrale, targetSliceIndex])

  useEffect(() => {
    if (targetSliceIndex === null || !coupeInfo) return
    const idx = Math.min(
      Math.max(targetSliceIndex, 0),
      Math.max(coupeInfo.nb_coupes - 1, 0),
    )
    setSliceIndex(idx)
    clearTargetSlice()
  }, [targetSliceIndex, coupeInfo, clearTargetSlice])

  const loadSlice = useCallback(
    async (index: number) => {
      const element = elementRef.current
      if (!element || !coupeInfo) return

      setLoadingSlice(true)
      setViewerError(null)

      try {
        initCornerstone()
        cornerstone.enable(element)

        const blob = await fetchSliceBlob(studyId, index, 'axial', windowCenter, windowWidth)
        const image = await loadPngBlobAsCornerstoneImage(
          blob,
          `mediscan-${studyId}-axial-${index}`,
        )
        cornerstone.displayImage(element, image)
        cornerstone.resize(element, true)

        if (!toolsReadyRef.current) {
          activateViewerTools(element)
          toolsReadyRef.current = true
        }
      } catch {
        setViewerError('Impossible de charger cette coupe')
      } finally {
        setLoadingSlice(false)
      }
    },
    [coupeInfo, studyId, windowCenter, windowWidth],
  )

  useEffect(() => {
    if (!coupeInfo) return
    void loadSlice(sliceIndex)
  }, [sliceIndex, coupeInfo, loadSlice])

  useEffect(() => {
    const element = elementRef.current
    const onResize = () => {
      if (element) {
        try {
          cornerstone.getEnabledElement(element)
          cornerstone.resize(element, true)
        } catch {
          /* pas encore activé */
        }
      }
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    const element = elementRef.current
    return () => {
      if (element) {
        try {
          cornerstone.disable(element)
        } catch {
          /* élément déjà désactivé */
        }
      }
      toolsReadyRef.current = false
    }
  }, [])

  const handleReset = () => {
    void loadSlice(sliceIndex)
  }

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
        <p className="text-sm text-danger">Volume DICOM indisponible</p>
      </div>
    )
  }

  const maxSlice = Math.max(coupeInfo.nb_coupes - 1, 0)

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex flex-wrap items-center gap-4 rounded-xl border border-border bg-bg-tertiary px-4 py-3">
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-secondary">Grad-CAM</span>
          <GradCamToggle
            active={gradCamActive}
            onChange={setGradCamActive}
            disabled={loadingSlice}
          />
        </div>

        {gradCamActive && (
          <div className="min-w-[180px] flex-1">
            <Slider
              label="Opacité overlay"
              min={0}
              max={100}
              value={gradCamOpacity}
              showValue
              valueLabel={`${gradCamOpacity}%`}
              onChange={(e) => setGradCamOpacity(Number(e.target.value))}
            />
          </div>
        )}

        {selectedVertebra && gradCamActive && (
          <span className="text-xs text-text-muted">
            Focalisation :{' '}
            <span className="font-mono text-accent-cyan">{selectedVertebra}</span>
          </span>
        )}
      </div>

      <div className="flex gap-3">
        <div className="relative min-w-0 flex-1 overflow-hidden rounded-xl border border-border bg-black">
          <div className={VIEWER_FRAME_CLASS}>
            <div className={VIEWER_INNER_CLASS}>
              <div
                ref={elementRef}
                className="absolute inset-0 cursor-crosshair"
                onContextMenu={(e) => e.preventDefault()}
              />

              <GradCamOverlay
                studyId={studyId}
                sliceNumber={sliceIndex}
                vertebraId={selectedVertebra ?? undefined}
                active={gradCamActive}
                opacity={gradCamOpacity}
                className="absolute inset-0"
              />
            </div>
          </div>

          {loadingSlice && (
            <div className="absolute inset-0 flex items-center justify-center bg-bg-primary/60">
              <LoadingSpinner size="md" />
            </div>
          )}

          {viewerError && (
            <div className="absolute inset-0 flex items-center justify-center bg-bg-primary/80">
              <p className="text-sm text-danger">{viewerError}</p>
            </div>
          )}

          <div className="pointer-events-none absolute bottom-3 left-3 rounded-lg border border-border bg-bg-primary/90 px-3 py-2 text-xs">
            <p className="font-mono text-accent-cyan">
              Coupe {sliceIndex + 1} / {coupeInfo.nb_coupes}
            </p>
            <p className="mt-1 text-text-muted">
              Clic gauche : windowing · Clic droit : pan · Molette : zoom
            </p>
          </div>

          <div className="absolute right-3 top-3">
            <Button variant="icon" aria-label="Réinitialiser la vue" onClick={handleReset}>
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
              aria-label="Navigation des coupes"
            />
          </div>
          <span className="font-mono text-[10px] text-text-muted">{sliceIndex + 1}</span>
        </div>
      </div>
    </div>
  )
}
