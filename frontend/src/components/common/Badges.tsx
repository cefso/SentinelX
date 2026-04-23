export function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
    info: 'bg-gray-100 text-gray-800',
  }

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${colors[severity] || colors.info}`}>
      {severity.toUpperCase()}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    firing: 'bg-red-100 text-red-800',
    resolved: 'bg-green-100 text-green-800',
    suppressed: 'bg-gray-100 text-gray-800',
    acknowledged: 'bg-yellow-100 text-yellow-800',
  }

  const labels: Record<string, string> = {
    firing: '触发中',
    resolved: '已恢复',
    suppressed: '已抑制',
    acknowledged: '已确认',
  }

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded whitespace-nowrap ${colors[status] || colors.firing}`}>
      {labels[status] || status}
    </span>
  )
}
