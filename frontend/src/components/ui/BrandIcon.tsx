import { GitBranch } from 'lucide-react'

interface BrandIconProps {
  size?: 'sm' | 'md' | 'lg'
}

export function BrandIcon({ size = 'md' }: BrandIconProps) {
  const sizeClasses = { sm: 'w-3 h-3', md: 'w-4 h-4', lg: 'w-5 h-5' }
  const containerClasses = {
    sm: 'w-4 h-4 border border-(--accent)/30',
    md: 'w-7 h-7 border border-(--accent)/40',
    lg: 'w-5 h-5 border border-(--accent)/30',
  }

  return (
    <div className={`${containerClasses[size]} bg-(--accent)/10 flex items-center justify-center`}>
      <GitBranch className={`${sizeClasses[size]} text-(--accent)`} />
    </div>
  )
}
