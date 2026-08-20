import { type LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  className?: string
}

export function EmptyState({ icon: Icon, title, description, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-12 text-center", className)}>
      {Icon && (
        <Icon className="w-12 h-12 text-muted-foreground/50 mb-4" />
      )}
      <h3 className="text-lg font-medium text-muted-foreground">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground/70 mt-1">{description}</p>
      )}
    </div>
  )
}
