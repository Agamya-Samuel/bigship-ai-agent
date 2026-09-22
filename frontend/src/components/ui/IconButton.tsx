import type { ReactNode } from 'react'

interface IconButtonProps {
  children: ReactNode
  onClick?: () => void
  ariaLabel?: string
  variant?: 'ghost' | 'subtle' | 'destructive'
  size?: 'sm' | 'md'
  disabled?: boolean
  className?: string
  title?: string
}

export function IconButton({
  children,
  onClick,
  ariaLabel,
  variant = 'ghost',
  size = 'md',
  disabled = false,
  className = '',
  title,
}: IconButtonProps) {
  const sizeClasses = {
    sm: 'w-8 h-8 [&_svg]:h-3.5 [&_svg]:w-3.5',
    md: 'w-9 h-9 [&_svg]:h-4 [&_svg]:w-4',
  }

  const variantClasses = {
    ghost:
      'text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]',
    subtle:
      'bg-[var(--bg-subtle)] text-[var(--text-secondary)] hover:bg-[var(--border-subtle)] hover:text-[var(--text-primary)]',
    destructive:
      'text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--danger)]',
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      title={title ?? ariaLabel}
      className={`${sizeClasses[size]} ${variantClasses[variant]} rounded-lg flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--bg-base)] ${className}`}
    >
      {children}
    </button>
  )
}