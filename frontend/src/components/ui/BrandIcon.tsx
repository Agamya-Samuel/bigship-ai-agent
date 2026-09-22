import { Ship } from 'lucide-react'

interface BrandIconProps {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function BrandIcon({ size = 'md', className = '' }: BrandIconProps) {
  const sizes = {
    sm: { box: 'w-7 h-7', icon: 'w-3.5 h-3.5', text: 'text-xs' },
    md: { box: 'w-8 h-8', icon: 'w-4 h-4', text: 'text-sm' },
    lg: { box: 'w-10 h-10', icon: 'w-5 h-5', text: 'text-base' },
  }
  const s = sizes[size]
  return (
    <div className={`${s.box} rounded-lg bg-[var(--accent)] text-white flex items-center justify-center shrink-0 ${className}`}>
      <Ship className={`${s.icon} text-white`} strokeWidth={2.25} />
    </div>
  )
}

export function BrandLogo({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const text = { sm: 'text-xs', md: 'text-sm', lg: 'text-base' }[size]
  return (
    <div className="flex items-center gap-2">
      <BrandIcon size={size} />
      <span className={`${text} font-semibold tracking-tight text-[var(--text-primary)]`}>Bigship</span>
    </div>
  )
}