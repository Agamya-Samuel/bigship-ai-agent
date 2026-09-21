import type { ReactNode } from 'react'

interface IconButtonProps {
  children: ReactNode
  onClick?: () => void
  ariaLabel?: string
  variant?: 'secondary' | 'destructive'
  className?: string
}

export function IconButton({ children, onClick, ariaLabel, variant = 'secondary', className = '' }: IconButtonProps) {
  const baseClasses = `p-2 min-w-11 min-h-11 border border-(--border-secondary) bg-(--bg-secondary) text-(--text-secondary) flex items-center justify-center transition-colors`

  const variantClasses = {
    secondary: 'hover:text-(--accent) hover:border-(--accent)/30',
    destructive: 'hover:text-red-500 hover:border-red-500/30',
  }

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      className={`${baseClasses} ${variantClasses[variant]}` + (className ? ` ${className}` : '')}
    >
      {children}
    </button>
  )
}
