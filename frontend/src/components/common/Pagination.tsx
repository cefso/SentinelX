import { ChevronLeft, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

interface PaginationProps {
  page: number
  totalPages: number
  total?: number
  onPageChange: (page: number) => void
  className?: string
  showTotal?: boolean
}

export function Pagination({
  page,
  totalPages,
  total,
  onPageChange,
  className,
  showTotal = true
}: PaginationProps) {
  if (totalPages <= 1) return null

  return (
    <div className={cn("flex items-center justify-between", className)}>
      {showTotal && total !== undefined && (
        <div className="text-sm text-muted-foreground">
          共 {total} 条记录
        </div>
      )}
      <div className="flex items-center gap-2 ml-auto">
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm text-muted-foreground">
          {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
