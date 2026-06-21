import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { fetchGradCamBlob, fetchSliceBlob } from '../../api/images'
import type { ScoreVertebre } from '../../types/analyse'
import { LoadingSpinner } from '../ui'

const MAX_IMAGES = 3

interface ReportReferenceImagesProps {
  studyId: string
  scores: ScoreVertebre[]
}

function pickReferenceScores(scores: ScoreVertebre[]): ScoreVertebre[] {
  const atRisk = scores
    .filter((s) => s.niveau_risque === 'eleve' || s.niveau_risque === 'incertain')
    .sort((a, b) => b.probabilite - a.probabilite)

  if (atRisk.length > 0) return atRisk.slice(0, MAX_IMAGES)

  if (scores.length === 0) return []
  return [scores.reduce((max, s) => (s.probabilite > max.probabilite ? s : max))]
}

function ReferenceImagePair({
  studyId,
  score,
}: {
  studyId: string
  score: ScoreVertebre
}) {
  const [sliceUrl, setSliceUrl] = useState<string | null>(null)
  const [gradCamUrl, setGradCamUrl] = useState<string | null>(null)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['report-ref-images', studyId, score.vertebre, score.coupe_reference],
    queryFn: async () => {
      const [sliceBlob, gradCamBlob] = await Promise.all([
        fetchSliceBlob(studyId, score.coupe_reference),
        fetchGradCamBlob(studyId, score.coupe_reference, score.vertebre),
      ])
      return { sliceBlob, gradCamBlob }
    },
  })

  useEffect(() => {
    if (!data) {
      setSliceUrl(null)
      setGradCamUrl(null)
      return
    }

    const slice = URL.createObjectURL(data.sliceBlob)
    const grad = URL.createObjectURL(data.gradCamBlob)
    setSliceUrl(slice)
    setGradCamUrl(grad)

    return () => {
      URL.revokeObjectURL(slice)
      URL.revokeObjectURL(grad)
    }
  }, [data])

  return (
    <div className="break-inside-avoid rounded-lg border border-gray-200 p-4">
      <p className="mb-3 text-sm font-semibold text-gray-800">
        {score.vertebre} — Coupe {score.coupe_reference + 1} ({(score.probabilite * 100).toFixed(1)} %)
      </p>
      {isLoading && (
        <div className="flex justify-center py-8">
          <LoadingSpinner size="sm" label="Chargement des images…" />
        </div>
      )}
      {isError && (
        <p className="text-sm text-gray-500">Images indisponibles pour {score.vertebre}</p>
      )}
      {sliceUrl && gradCamUrl && (
        <div className="grid grid-cols-2 gap-4">
          <figure>
            <img
              src={sliceUrl}
              alt={`Coupe axiale ${score.vertebre}`}
              className="w-full rounded border border-gray-200 bg-black object-contain"
            />
            <figcaption className="mt-1 text-center text-xs text-gray-500">Coupe axiale</figcaption>
          </figure>
          <figure>
            <img
              src={gradCamUrl}
              alt={`Grad-CAM ${score.vertebre}`}
              className="w-full rounded border border-gray-200 bg-black object-contain"
            />
            <figcaption className="mt-1 text-center text-xs text-gray-500">Grad-CAM</figcaption>
          </figure>
        </div>
      )}
    </div>
  )
}

export function ReportReferenceImages({ studyId, scores }: ReportReferenceImagesProps) {
  const referenceScores = pickReferenceScores(scores)

  if (referenceScores.length === 0) return null

  return (
    <section className="mt-8">
      <h2 className="mb-4 border-b border-gray-300 pb-2 text-lg font-semibold text-gray-900">
        Images de référence
      </h2>
      <div className="space-y-6">
        {referenceScores.map((score) => (
          <ReferenceImagePair key={score.vertebre} studyId={studyId} score={score} />
        ))}
      </div>
    </section>
  )
}
