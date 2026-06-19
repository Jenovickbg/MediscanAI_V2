import { motion } from 'framer-motion'

import { cn } from '../../utils/cn'

interface GradCamToggleProps {
  active: boolean
  onChange: (active: boolean) => void
  disabled?: boolean
}

export function GradCamToggle({ active, onChange, disabled }: GradCamToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      disabled={disabled}
      onClick={() => onChange(!active)}
      className={cn(
        'relative inline-flex h-7 w-12 shrink-0 items-center rounded-full border transition-colors',
        active ? 'border-accent-cyan bg-accent-cyan/20' : 'border-border bg-bg-elevated',
        disabled && 'cursor-not-allowed opacity-50',
      )}
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        className={cn(
          'absolute h-5 w-5 rounded-full shadow-sm',
          active ? 'bg-accent-cyan' : 'bg-text-muted',
        )}
        style={{ left: active ? 'calc(100% - 1.375rem)' : '0.25rem' }}
      />
      <span className="sr-only">Activer Grad-CAM</span>
    </button>
  )
}
