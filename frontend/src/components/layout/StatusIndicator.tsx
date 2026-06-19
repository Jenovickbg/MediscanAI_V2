import { useQuery } from '@tanstack/react-query'

import { fetchHealth } from '../../api/health'
import { cn } from '../../utils/cn'

export function StatusIndicator() {
  const { data, isError, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
    retry: 1,
  })

  const isOnline = !isError && data?.status === 'ok'
  const modelLoaded = isOnline && data?.model_loaded === true

  let label = 'Modèle non disponible'
  let dotClass = 'bg-danger'

  if (isLoading) {
    label = 'Vérification…'
    dotClass = 'bg-warning'
  } else if (isOnline && modelLoaded) {
    label = 'Modèle IA chargé'
    dotClass = 'bg-safe'
  } else if (isOnline) {
    label = 'API disponible — modèle absent'
    dotClass = 'bg-warning'
  }

  return (
    <div className="flex items-center gap-2 rounded-lg border border-border bg-bg-tertiary px-3 py-2">
      <span
        className={cn('h-2 w-2 shrink-0 rounded-full', dotClass, {
          'animate-mediscan-pulse': isOnline && (modelLoaded || isLoading),
        })}
        aria-hidden="true"
      />
      <span className="text-xs text-text-secondary">{label}</span>
    </div>
  )
}
