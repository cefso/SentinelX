import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const severityVariants: Record<string, string> = {
  critical: "bg-red-100 text-red-800 border-red-200 hover:bg-red-100",
  high: "bg-orange-100 text-orange-800 border-orange-200 hover:bg-orange-100",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200 hover:bg-yellow-100",
  low: "bg-blue-100 text-blue-800 border-blue-200 hover:bg-blue-100",
  info: "bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-100",
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <Badge variant="outline" className={cn(severityVariants[severity] || severityVariants.info)}>
      {severity.toUpperCase()}
    </Badge>
  )
}

const statusVariants: Record<string, string> = {
  firing: "bg-red-100 text-red-800 border-red-200 hover:bg-red-100",
  resolved: "bg-green-100 text-green-800 border-green-200 hover:bg-green-100",
  suppressed: "bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-100",
  acknowledged: "bg-blue-100 text-blue-800 border-blue-200 hover:bg-blue-100",
  deduplicated: "bg-yellow-100 text-yellow-800 border-yellow-200 hover:bg-yellow-100",
}

const statusLabels: Record<string, string> = {
  firing: "触发中",
  resolved: "已恢复",
  suppressed: "已抑制",
  acknowledged: "已确认",
  deduplicated: "已去重",
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant="outline" className={cn(statusVariants[status] || statusVariants.firing)}>
      {statusLabels[status] || status}
    </Badge>
  )
}
