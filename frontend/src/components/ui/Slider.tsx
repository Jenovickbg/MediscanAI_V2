import type { InputHTMLAttributes } from 'react'

import { cn } from '../../utils/cn'

interface SliderProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string
  showValue?: boolean
  valueLabel?: string
}

export function Slider({
  label,
  showValue = false,
  valueLabel,
  className,
  id,
  value,
  min = 0,
  max = 100,
  ...props
}: SliderProps) {
  const inputId = id ?? label?.toLowerCase().replace(/\s+/g, '-')

  return (
    <div className={cn('w-full', className)}>
      {(label || showValue) && (
        <div className="mb-2 flex items-center justify-between">
          {label && (
            <label htmlFor={inputId} className="text-xs text-text-secondary">
              {label}
            </label>
          )}
          {showValue && (
            <span className="font-mono text-xs text-accent-cyan">
              {valueLabel ?? String(value ?? min)}
            </span>
          )}
        </div>
      )}
      <input
        id={inputId}
        type="range"
        min={min}
        max={max}
        value={value}
        className={cn(
          'mediscan-slider h-2 w-full cursor-pointer appearance-none rounded-full',
          'bg-bg-elevated accent-accent-blue',
          '[&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4',
          '[&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full',
          '[&::-webkit-slider-thumb]:bg-accent-blue [&::-webkit-slider-thumb]:shadow-md',
          '[&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-110',
          '[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full',
          '[&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-accent-blue',
        )}
        {...props}
      />
    </div>
  )
}
