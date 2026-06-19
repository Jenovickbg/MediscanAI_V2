import { useEffect, useState } from 'react'

interface ClockState {
  date: string
  time: string
}

function formatClock(now: Date): ClockState {
  return {
    date: now.toLocaleDateString('fr-FR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    }),
    time: now.toLocaleTimeString('fr-FR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }),
  }
}

export function useClock(): ClockState {
  const [clock, setClock] = useState<ClockState>(() => formatClock(new Date()))

  useEffect(() => {
    const interval = window.setInterval(() => {
      setClock(formatClock(new Date()))
    }, 1000)

    return () => window.clearInterval(interval)
  }, [])

  return clock
}
