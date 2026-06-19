import type { HTMLAttributes, ReactNode } from 'react'

import { cn } from '../../utils/cn'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
}

interface CardSectionProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode
  className?: string
}

export function Card({ children, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'overflow-hidden rounded-xl border border-border bg-bg-tertiary',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className, ...props }: CardSectionProps) {
  return (
    <div
      className={cn(
        'border-b border-border px-4 py-3 text-sm font-semibold text-text-primary',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardBody({ children, className, ...props }: CardSectionProps) {
  return (
    <div className={cn('px-4 py-4 text-sm text-text-secondary', className)} {...props}>
      {children}
    </div>
  )
}

export function CardFooter({ children, className, ...props }: CardSectionProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 border-t border-border bg-bg-secondary/50 px-4 py-3',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}
