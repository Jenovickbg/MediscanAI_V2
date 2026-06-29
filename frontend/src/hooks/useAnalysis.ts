import { useCallback, useEffect, useRef, useState } from 'react'
import { isAxiosError } from 'axios'

import {
  fetchAnalysisResults,
  fetchAnalysisStatus,
  startAnalysis,
} from '../api/analyse'
import type { AnalyseStatus, ResultatAnalyse } from '../types/analyse'

interface UseAnalysisResult {
  status: AnalyseStatus['status'] | 'idle'
  progress: number
  message: string
  result: ResultatAnalyse | null
  error: string | null
  isRunning: boolean
  isSlow: boolean
  retry: () => void
}

function formatAnalysisError(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    if (err.code === 'ECONNABORTED') {
      return 'Le serveur met du temps à répondre (analyse CPU en cours). Patientez…'
    }
    const detail = err.response?.data?.detail
    if (typeof detail === 'string' && detail.length > 0) {
      return detail
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => String(item)).join(', ')
    }
    if (err.response?.status === 500 || err.response?.status === 502 || err.response?.status === 503) {
      return 'Serveur temporairement indisponible (analyse CPU en cours). Nouvelle tentative…'
    }
  }
  return err instanceof Error ? err.message : fallback
}

function isTransientError(err: unknown): boolean {
  if (!isAxiosError(err)) return false
  if (err.code === 'ECONNABORTED') return true
  const status = err.response?.status
  return status === 500 || status === 502 || status === 503
}

export function useAnalysis(studyId: string | undefined): UseAnalysisResult {
  const [status, setStatus] = useState<AnalyseStatus['status'] | 'idle'>('idle')
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [result, setResult] = useState<ResultatAnalyse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSlow, setIsSlow] = useState(false)
  const startedRef = useRef(false)
  const pollRef = useRef<number | null>(null)
  const completedRef = useRef(false)
  const progressRef = useRef({ value: 0, at: Date.now() })

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const markProgress = useCallback((value: number) => {
    setProgress(value)
    if (value !== progressRef.current.value) {
      progressRef.current = { value, at: Date.now() }
      setIsSlow(false)
    } else if (Date.now() - progressRef.current.at > 120_000) {
      setIsSlow(true)
    }
  }, [])

  const pollStatus = useCallback(
    async (studyIdValue: string) => {
      const taskStatus = await fetchAnalysisStatus(studyIdValue)
      setError(null)
      setStatus(taskStatus.status)
      markProgress(taskStatus.progress)

      if (taskStatus.status === 'error') {
        setError(taskStatus.error ?? 'Analyse échouée')
        setMessage(taskStatus.error ?? 'Analyse échouée')
        stopPolling()
        return 'error' as const
      }

      if (taskStatus.status === 'done') {
        const results = await fetchAnalysisResults(studyIdValue)
        setResult(results)
        setStatus('done')
        setProgress(100)
        setMessage('Analyse terminée.')
        completedRef.current = true
        stopPolling()
        return 'done' as const
      }

      setMessage(
        taskStatus.progress > 0
          ? `Analyse en cours… ${taskStatus.progress} %`
          : 'Analyse en cours…',
      )
      return 'running' as const
    },
    [markProgress, stopPolling],
  )

  const runAnalysis = useCallback(
    async (force = false) => {
      if (!studyId) return

      stopPolling()
      setError(null)
      setIsSlow(false)
      setStatus('running')
      setProgress(0)
      setMessage('Lancement de l’analyse…')
      progressRef.current = { value: 0, at: Date.now() }
      completedRef.current = false

      try {
        await startAnalysis(studyId, force)
        const initial = await pollStatus(studyId)
        if (initial === 'done' || initial === 'error') return

        pollRef.current = window.setInterval(() => {
          void pollStatus(studyId).catch((err) => {
            if (isTransientError(err)) {
              setIsSlow(true)
              setMessage(formatAnalysisError(err, 'Serveur occupé — nouvelle tentative…'))
              return
            }
            setError(formatAnalysisError(err, 'Erreur de suivi'))
            setStatus('error')
            stopPolling()
          })
        }, 2000)
      } catch (err) {
        if (isTransientError(err)) {
          setIsSlow(true)
          setMessage(formatAnalysisError(err, 'Lancement en attente…'))
          pollRef.current = window.setInterval(() => {
            void pollStatus(studyId).catch(() => undefined)
          }, 3000)
          return
        }
        setError(formatAnalysisError(err, 'Erreur lors du lancement'))
        setStatus('error')
      }
    },
    [studyId, pollStatus, stopPolling],
  )

  useEffect(() => {
    if (!studyId || startedRef.current) return
    startedRef.current = true
    void runAnalysis(false)
  }, [studyId, runAnalysis])

  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  const isRunning = (status === 'running' || status === 'pending') && !error

  return {
    status,
    progress,
    message,
    result,
    error,
    isRunning,
    isSlow,
    retry: () => {
      startedRef.current = true
      setResult(null)
      void runAnalysis(true)
    },
  }
}
