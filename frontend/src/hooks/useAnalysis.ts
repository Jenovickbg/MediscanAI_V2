import { useCallback, useEffect, useRef, useState } from 'react'

import {
  fetchAnalysisResults,
  fetchAnalysisStatus,
  startAnalysis,
} from '../api/analyse'
import type { AnalyseStatus, ResultatAnalyse } from '../types/analyse'

interface UseAnalysisResult {
  status: AnalyseStatus['status'] | 'idle'
  progress: number
  result: ResultatAnalyse | null
  error: string | null
  isRunning: boolean
  retry: () => void
}

export function useAnalysis(studyId: string | undefined): UseAnalysisResult {
  const [status, setStatus] = useState<AnalyseStatus['status'] | 'idle'>('idle')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<ResultatAnalyse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const startedRef = useRef(false)

  const runAnalysis = useCallback(async () => {
    if (!studyId) return

    setError(null)
    setStatus('running')
    setProgress(0)

    try {
      await startAnalysis(studyId)
      const taskStatus = await fetchAnalysisStatus(studyId)
      setStatus(taskStatus.status)
      setProgress(taskStatus.progress)

      if (taskStatus.status === 'done') {
        const results = await fetchAnalysisResults(studyId)
        setResult(results)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors du lancement')
      setStatus('error')
    }
  }, [studyId])

  useEffect(() => {
    if (!studyId || startedRef.current) return
    startedRef.current = true
    void runAnalysis()
  }, [studyId, runAnalysis])

  useEffect(() => {
    if (!studyId || status === 'done' || status === 'error' || status === 'idle') {
      return
    }

    const interval = window.setInterval(async () => {
      try {
        const taskStatus = await fetchAnalysisStatus(studyId)
        setStatus(taskStatus.status)
        setProgress(taskStatus.progress)

        if (taskStatus.status === 'done') {
          const results = await fetchAnalysisResults(studyId)
          setResult(results)
          window.clearInterval(interval)
        }

        if (taskStatus.status === 'error') {
          setError(taskStatus.error ?? 'Analyse échouée')
          window.clearInterval(interval)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur de suivi')
        setStatus('error')
        window.clearInterval(interval)
      }
    }, 1000)

    return () => window.clearInterval(interval)
  }, [studyId, status])

  return {
    status,
    progress,
    result,
    error,
    isRunning: status === 'running' || status === 'pending',
    retry: () => {
      startedRef.current = false
      setResult(null)
      void runAnalysis()
    },
  }
}
