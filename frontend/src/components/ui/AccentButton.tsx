import type { ButtonHTMLAttributes, ReactNode } from 'react'

interface AccentButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

export function AccentButton({
  children,
  size = 'md',
  className = '',
  loading = false,
  disabled,
  type = 'button',
  ...rest
}: AccentButtonProps) {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-1.5 text-xs',
    lg: 'px-6 py-3 text-sm',
  }

  return (
    <button
      type={type}
      disabled={disabled || loading}
      {...rest}
      className={
        `${sizeClasses[size]} bg-(--accent) text-(--bg-primary) ` +
        `font-semibold uppercase tracking-widest hover:bg-(--accent-hover) ` +
        `transition-colors flex items-center justify-center gap-2 min-h-11` +
        (className ? ` ${className}` : '')
      }
    >
      {children}
    </button>
  )
}
