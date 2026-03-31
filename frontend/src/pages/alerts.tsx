import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { AlertResponse, AlertStats } from '@/types/alert'

export function AlertsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [filters, setFilters] = useState({
    status: '',
    severity: '',
    source: '',
    keyword: '',
  })

  const { data: stats } = useQuery<AlertStats>({
    queryKey: ['alertStats'],
    queryFn: () => apiClient.get('/alerts/stats'),
  })

  const { data: alerts, isLoading, refetch } = useQuery<{ items: AlertResponse[]; total: number; page: number; page_size: number }>({
    queryKey: ['alerts', page, pageSize, filters],
    queryFn: () => apiClient.get('/alerts', {
      page,
      page_size: pageSize,
      status: filters.status || undefined,
      severity: filters.severity || undefined,
      source: filters.source || undefined,
      keyword: filters.keyword || undefined,
    }),
  })

  const totalPages = Math.ceil((alerts?.total || 0) / pageSize)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">告警列表</h1>
        <p className="text-gray-600">管理和监控所有告警事件</p>
      </div>

      <div className="grid grid-cols-5 gap-4">
        <StatCard title="总告警" value={stats?.total || 0} color="blue" />
        <StatCard title="触发中" value={stats?.firing || 0} color="red" />
        <StatCard title="已恢复" value={stats?.resolved || 0} color="green" />
        <StatCard title="已抑制" value={stats?.suppressed || 0} color="gray" />
        <StatCard title="未分配" value={stats?.unassigned || 0} color="yellow" />
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b space-y-3">
          <input
            type="text"
            placeholder="搜索告警标题或内容..."
            className="w-full px-3 py-2 border rounded-md"
            value={filters.keyword}
            onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
          />
          <div className="flex gap-3 flex-wrap">
            <select
              className="px-3 py-2 border rounded-md"
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            >
              <option value="">全部状态</option>
              <option value="firing">触发中</option>
              <option value="resolved">已恢复</option>
              <option value="suppressed">已抑制</option>
              <option value="acknowledged">已确认</option>
            </select>
            <select
              className="px-3 py-2 border rounded-md"
              value={filters.severity}
              onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
            >
              <option value="">全部级别</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
            <select
              className="px-3 py-2 border rounded-md"
              value={filters.source}
              onChange={(e) => setFilters({ ...filters, source: e.target.value })}
            >
              <option value="">全部来源</option>
              <option value="prometheus">Prometheus</option>
              <option value="alertmanager">Alertmanager</option>
              <option value="zabbix">Zabbix</option>
              <option value="aliyun">阿里云</option>
              <option value="tencent">腾讯云</option>
              <option value="custom">自定义</option>
            </select>
            <button
              onClick={() => { setPage(1); refetch(); }}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
            >
              搜索
            </button>
            <button
              onClick={() => setFilters({ status: '', severity: '', source: '', keyword: '' })}
              className="px-4 py-2 border rounded-md hover:bg-gray-50"
            >
              重置
            </button>
          </div>
        </div>

        <div className="divide-y">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">加载中...</div>
          ) : alerts?.items.length === 0 ? (
            <div className="p-8 text-center text-gray-500">暂无告警</div>
          ) : (
            alerts?.items.map((alert) => (
              <div
                key={alert.id}
                className="p-4 hover:bg-gray-50 cursor-pointer"
                onClick={() => navigate(`/alerts/${alert.id}`)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={alert.severity} />
                    <div>
                      <div className="font-medium">{alert.title}</div>
                      <div className="text-sm text-gray-500">
                        {alert.source} • {alert.fired_at ? new Date(alert.fired_at).toLocaleString('zh-CN') : ''}
                        {alert.fire_count > 1 && <span className="ml-2 text-orange-500">×{alert.fire_count}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {alert.trace_id && (
                      <span className="text-xs text-gray-400">Trace: {alert.trace_id}</span>
                    )}
                    <StatusBadge status={alert.status} />
                  </div>
                </div>
                {alert.labels && Object.keys(alert.labels).length > 0 && (
                  <div className="mt-2 flex gap-1 flex-wrap">
                    {Object.entries(alert.labels).slice(0, 5).map(([key, value]) => (
                      <span key={key} className="text-xs bg-gray-100 px-2 py-0.5 rounded">
                        {key}: {String(value)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {totalPages > 1 && (
          <div className="p-4 border-t flex items-center justify-between">
            <div className="text-sm text-gray-500">
              共 {alerts?.total} 条，第 {page} / {totalPages} 页
            </div>
            <div className="flex gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-50"
              >
                上一页
              </button>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                className="px-3 py-1 border rounded disabled:opacity-50 hover:bg-gray-50"
              >
                下一页
              </button>
            </div>
          </div>
        )}
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
