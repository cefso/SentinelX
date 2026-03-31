import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { AlertResponse, AlertStats } from '@/types/alert'

export function AlertsPage() {
  const { data: stats } = useQuery<AlertStats>({
    queryKey: ['alertStats'],
    queryFn: () => apiClient.get('/alerts/stats'),
  })

  const { data: alerts, isLoading } = useQuery<{ items: AlertResponse[]; total: number }>({
    queryKey: ['alerts'],
    queryFn: () => apiClient.get('/alerts', { page: 1, page_size: 20 }),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">告警列表</h1>
        <p className="text-gray-600">管理和监控所有告警事件</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard title="总告警" value={stats?.total || 0} color="blue" />
        <StatCard title="触发中" value={stats?.firing || 0} color="red" />
        <StatCard title="已恢复" value={stats?.resolved || 0} color="green" />
        <StatCard title="已抑制" value={stats?.suppressed || 0} color="gray" />
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <input
            type="text"
            placeholder="搜索告警..."
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
        <div className="divide-y">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">加载中...</div>
          ) : alerts?.items.length === 0 ? (
            <div className="p-8 text-center text-gray-500">暂无告警</div>
          ) : (
            alerts?.items.map((alert) => (
              <div key={alert.id} className="p-4 hover:bg-gray-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={alert.severity} />
                    <div>
                      <div className="font-medium">{alert.title}</div>
                      <div className="text-sm text-gray-500">
                        {alert.source} • {alert.fired_at}
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={alert.status} />
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, color }: { title: string; value: number; color: string }) {
  const colors = {
    blue: 'bg-blue-50 text-blue-700',
    red: 'bg-red-50 text-red-700',
    green: 'bg-green-50 text-green-700',
    gray: 'bg-gray-50 text-gray-700',
  }

  return (
    <div className={`p-4 rounded-lg ${colors[color as keyof typeof colors]}`}>
      <div className="text-sm font-medium">{title}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
    info: 'bg-gray-100 text-gray-800',
  }

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${colors[severity as keyof typeof colors] || colors.info}`}>
      {severity.toUpperCase()}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    firing: 'bg-red-100 text-red-800',
    resolved: 'bg-green-100 text-green-800',
    suppressed: 'bg-gray-100 text-gray-800',
  }

  const labels = {
    firing: '触发中',
    resolved: '已恢复',
    suppressed: '已抑制',
  }

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${colors[status as keyof typeof colors] || colors.firing}`}>
      {labels[status as keyof typeof labels] || status}
    </span>
  )
}
