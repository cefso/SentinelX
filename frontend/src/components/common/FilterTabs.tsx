import { cn } from '@/lib/utils'

interface FilterTab {
  key: string
  label: string
  count?: number
}

interface FilterTabsProps {
  tabs: FilterTab[]
  active: string
  onChange: (key: string) => void
  className?: string
}

export function FilterTabs({ tabs, active, onChange, className }: FilterTabsProps) {
  return (
    <div className={cn("flex gap-2 flex-wrap", className)}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={cn(
            "px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
            active === tab.key
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
          )}
        >
          {tab.label}
          {tab.count !== undefined && ` (${tab.count})`}
        </button>
      ))}
    </div>
  )
}
