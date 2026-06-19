import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { fetchSliceBlob } from '../../api/images'
import { LoadingSpinner } from '../ui'

interface ImportPreviewSliceProps {
  studyId: string
  sliceNumber: number
}

export function ImportPreviewSlice({ studyId, sliceNumber }: ImportPreviewSliceProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['import-preview', studyId, sliceNumber],
    queryFn: () => fetchSliceBlob(studyId, sliceNumber),
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

  if (isLoading) {
    return (
      <div className="flex aspect-square items-center justify-center bg-bg-primary">
        <LoadingSpinner size="sm" />
      </div>
    )
  }

  if (isError || !blobUrl) {
    return (
      <div className="flex aspect-square items-center justify-center bg-bg-primary text-xs text-text-muted">
        Aperçu indisponible
      </div>
    )
  }

  return (
    <img
      src={blobUrl}
      alt={`Coupe axiale ${sliceNumber + 1}`}
      className="aspect-square w-full object-cover"
    />
  )
}
