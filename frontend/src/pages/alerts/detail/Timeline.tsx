import { AlertCircle, CheckCircle, XCircle } from 'lucide-react'
import { formatLocalDateTime } from '@/utils/datetime'
import type { AlertResponse } from '@/types/alert'

interface TimelineItem {
  time: string
  event: string
  icon: React.ComponentType<{ className?: string }>
  color: string
}

export function buildTimeline(alert: AlertResponse): TimelineItem[] {
  const timeline: TimelineItem[] = []
  if (alert.fired_at) {
    timeline.push({ time: alert.fired_at, event: '告警触发', icon: AlertCircle, color: 'text-red-500' })
  }
  if (alert.acknowledged_at) {
    timeline.push({ time: alert.acknowledged_at, event: '已确认', icon: CheckCircle, color: 'text-yellow-500' })
  }
  if (alert.resolved_at) {
    timeline.push({ time: alert.resolved_at, event: '已解决', icon: CheckCircle, color: 'text-green-500' })
  }
  if (alert.silenced_until) {
    timeline.push({ time: alert.silenced_until, event: '已静默', icon: XCircle, color: 'text-gray-500' })
  }
  return timeline
}

export function Timeline({ timeline }: { timeline: TimelineItem[] }) {
  if (timeline.length === 0) return null

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">处理时间线</h2>
      <div className="relative">
        <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-gray-200" />
        <div className="space-y-2">
          {timeline.map((item, index) => {
            const Icon = item.icon
            return (
              <div key={index} className="relative flex items-start gap-3 pl-8">
                <div className={`absolute left-0 w-4 h-4 rounded-full bg-white border-2 ${item.color.replace('text-', 'border-')}`}>
                  <Icon className={`w-3 h-3 absolute top-0.5 left-0.5 ${item.color}`} />
                </div>
                <div className="flex-1">
                  <div className="font-medium text-sm">{item.event}</div>
                  <div className="text-xs text-gray-500">
                    {formatLocalDateTime(item.time)}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
