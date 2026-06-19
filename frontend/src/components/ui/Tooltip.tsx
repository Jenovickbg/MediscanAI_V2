import type { ReactNode } from 'react'

import { cn } from '../../utils/cn'

type TooltipPosition = 'top' | 'bottom' | 'left' | 'right'

interface TooltipProps {
  content: string
  children: ReactNode
  position?: TooltipPosition
  className?: string
}

const positionStyles: Record<TooltipPosition, string> = {
  top: 'bottom-full left-1/2 mb-2 -translate-x-1/2',
  bottom: 'top-full left-1/2 mt-2 -translate-x-1/2',
  left: 'right-full top-1/2 mr-2 -translate-y-1/2',
  right: 'left-full top-1/2 ml-2 -translate-y-1/2',
}

export function Tooltip({
  content,
  children,
  position = 'top',
  className,
}: TooltipProps) {
  return (
    <span className={cn('group relative inline-flex', className)}>
      {children}
      <span
        role="tooltip"
        className={cn(
          'pointer-events-none absolute z-50 whitespace-nowrap rounded-md',
          'border border-border-light bg-bg-elevated px-2 py-1 text-xs text-text-primary',
          'opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100',
          'group-focus-within:opacity-100',
          positionStyles[position],
        )}
      >
        {content}
      </span>
    </span>
  )
}
