import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { fetchGradCamBlob } from '../../api/images'
import { cn } from '../../utils/cn'
import { LoadingSpinner } from '../ui'

interface VertebraGradCamThumbnailProps {
  studyId: string
  sliceNumber: number
  vertebraId: string
  className?: string
}

export function VertebraGradCamThumbnail({
  studyId,
  sliceNumber,
  vertebraId,
  className,
}: VertebraGradCamThumbnailProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['gradcam-thumbnail', studyId, sliceNumber, vertebraId],
    queryFn: () => fetchGradCamBlob(studyId, sliceNumber, vertebraId),
    staleTime: 120_000,
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
    <div
      className={cn(
        'relative aspect-square overflow-hidden rounded-lg border border-border bg-bg-primary',
        className,
      )}
    >
      {isLoading && (
        <div className="flex h-full items-center justify-center">
          <LoadingSpinner size="sm" label="Chargement…" />
        </div>
      )}

      {isError && (
        <div className="flex h-full items-center justify-center p-2 text-center">
          <span className="text-xs text-text-muted">Miniature indisponible</span>
        </div>
      )}

      {blobUrl && !isLoading && (
        <img
          src={blobUrl}
          alt={`Coupe ${sliceNumber + 1} avec Grad-CAM ${vertebraId}`}
          className="h-full w-full object-contain"
        />
      )}
    </div>
  )
}
