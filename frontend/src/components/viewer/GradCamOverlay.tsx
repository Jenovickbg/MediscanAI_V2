import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'

import { fetchGradCamBlob } from '../../api/images'
import { cn } from '../../utils/cn'
import { LoadingSpinner } from '../ui'

interface GradCamOverlayProps {
  studyId: string
  sliceNumber: number
  vertebraId?: string
  active: boolean
  opacity: number
  className?: string
}

export function GradCamOverlay({
  studyId,
  sliceNumber,
  vertebraId,
  active,
  opacity,
  className,
}: GradCamOverlayProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['gradcam', studyId, sliceNumber, vertebraId],
    queryFn: () => fetchGradCamBlob(studyId, sliceNumber, vertebraId),
    enabled: active,
    staleTime: 60_000,
  })

  useEffect(() => {
    if (!data) {
      setBlobUrl(null)
      return
    }

    const url = URL.createObjectURL(data)
    setBlobUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [data])

  return (
    <AnimatePresence>
      {active && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className={cn('pointer-events-none absolute inset-0 overflow-hidden', className)}
          aria-hidden={!active}
        >
          {isLoading && (
            <div className="flex h-full items-center justify-center bg-bg-primary/20">
              <LoadingSpinner size="sm" label="Grad-CAM…" />
            </div>
          )}

          {isError && (
            <div className="flex h-full items-center justify-center">
              <span className="rounded bg-bg-primary/80 px-2 py-1 text-xs text-danger">
                Grad-CAM indisponible
              </span>
            </div>
          )}

          {blobUrl && !isLoading && (
            <img
              src={blobUrl}
              alt=""
              className="h-full w-full object-contain"
              style={{
                mixBlendMode: 'screen',
                opacity: opacity / 100,
              }}
            />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
