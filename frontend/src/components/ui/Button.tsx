import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '../../utils/cn'
import { LoadingSpinner } from './LoadingSpinner'

type ButtonVariant = 'primary' | 'ghost' | 'danger' | 'icon'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  loading?: boolean
  icon?: ReactNode
  children?: ReactNode
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-accent-blue text-white hover:bg-[#4a9ae8] border border-accent-blue shadow-sm',
  ghost:
    'bg-transparent text-text-primary hover:bg-bg-elevated border border-border hover:border-border-light',
  danger:
    'bg-danger/15 text-danger hover:bg-danger/25 border border-danger/40',
  icon:
    'bg-bg-elevated text-text-secondary hover:text-text-primary hover:bg-bg-tertiary border border-border p-2',
}

export function Button({
  variant = 'primary',
  loading = false,
  icon,
  children,
  className,
  disabled,
  type = 'button',
  ...props
}: ButtonProps) {
  const isIconOnly = variant === 'icon' || (icon !== undefined && children === undefined)

  return (
    <button
      type={type}
      disabled={disabled ?? loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan/50',
        'disabled:pointer-events-none disabled:opacity-50',
        isIconOnly ? 'h-9 w-9 p-0' : 'h-9 px-4 text-sm',
        variantStyles[variant],
        className,
      )}
      {...props}
    >
      {loading ? (
        <LoadingSpinner size="sm" />
      ) : (
        <>
          {icon}
          {children}
        </>
      )}
    </button>
  )
}
