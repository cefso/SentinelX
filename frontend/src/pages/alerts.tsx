import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { AlertResponse, AlertStats, AlertAggregatedItem } from '@/types/alert'
import { useCloudMetricsMap } from '@/hooks/useCloudMetrics'
import { formatLocalDateTime } from '@/utils/datetime'

interface AlertSource {
  id: number
  name: string
  code: string
  source_type: string
  config: Record<string, any>
  description?: string
  is_active: boolean
  alert_count: number
  last_alert_at?: string
  created_at: string
}
import { Bell, AlertTriangle, AlertCircle, XCircle, ChevronLeft, ChevronRight, Search, RotateCcw, Fingerprint } from 'lucide-react'

export function AlertsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState({
    status: '',
    severity: '',
    sourceId: '' as number | '',
    keyword: '',
    fingerprint: '',
  })
  const [aggregateMode, setAggregateMode] = useState(true)

  // 初始化从 URL 参数
  useEffect(() => {
    const fp = searchParams.get('fingerprint')
    const agg = searchParams.get('aggregate')
    if (fp) {
      setFilters(prev => ({ ...prev, fingerprint: fp }))
      setPage(1)
    }
    if (agg === 'false') {
      setAggregateMode(false)
    }
  }, [searchParams])

  const { data: stats } = useQuery<AlertStats>({
    queryKey: ['alertStats'],
    queryFn: () => apiClient.get('/alerts/stats'),
  })

  const { data: sources = [] } = useQuery<AlertSource[]>({
    queryKey: ['alert-sources'],
    queryFn: () => apiClient.get('/sources'),
  })

  // 查询去重后的触发中告警数量
  const { data: firingAlerts } = useQuery<{ items: AlertAggregatedItem[]; total: number }>({
    queryKey: ['alerts-dedup', 'firing'],
    queryFn: () => apiClient.get('/alerts', {
      page: 1,
      page_size: 1,
      status: 'firing',
      aggregate: true,
    }),
  })

  // 查询去重后的 Critical 告警数量
  const { data: criticalAlerts } = useQuery<{ items: AlertAggregatedItem[]; total: number }>({
    queryKey: ['alerts-dedup', 'critical'],
    queryFn: () => apiClient.get('/alerts', {
      page: 1,
      page_size: 1,
      status: 'firing',
      severity: 'critical',
      aggregate: true,
    }),
  })

  // 查询去重后的 High 告警数量
  const { data: highAlerts } = useQuery<{ items: AlertAggregatedItem[]; total: number }>({
    queryKey: ['alerts-dedup', 'high'],
    queryFn: () => apiClient.get('/alerts', {
      page: 1,
      page_size: 1,
      status: 'firing',
      severity: 'high',
      aggregate: true,
    }),
  })

  const { data: alerts, isLoading, refetch } = useQuery<{ items: AlertResponse[]; total: number; page: number; page_size: number }>({
    queryKey: ['alerts', page, pageSize, filters, aggregateMode],
    queryFn: () => apiClient.get('/alerts', {
      page,
      page_size: pageSize,
      status: filters.status || undefined,
      severity: filters.severity || undefined,
      source_id: filters.sourceId || undefined,
      keyword: filters.keyword || undefined,
      fingerprint: filters.fingerprint || undefined,
      aggregate: aggregateMode || undefined,
    }),
  })

  const { data: cloudMetricsMap } = useCloudMetricsMap()

  const getProductDisplayName = (namespace: string) => {
    if (!cloudMetricsMap || !namespace) return namespace || '-'
    const records = cloudMetricsMap[namespace]
    // 优先使用 namespace_desc，否则使用 product，否则使用原始 namespace
    return records?.[0]?.namespace_desc || records?.[0]?.product || namespace || '-'
  }

  const totalPages = Math.ceil((alerts?.total || 0) / pageSize)

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">告警列表</h1>

      {/* 统计卡片 - 5个带渐变和图标 */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="总告警"
          value={stats?.total || 0}
          subtitle="全部告警"
          icon={Bell}
          gradient="from-blue-500 to-blue-600"
        />
        <StatCard
          title="去重告警"
          value={stats?.unique || 0}
          subtitle="不同指纹"
          icon={Fingerprint}
          gradient="from-purple-500 to-purple-600"
        />
        <StatCard
          title="触发中"
          value={firingAlerts?.total || 0}
          subtitle="正在触发"
          icon={AlertTriangle}
          gradient="from-orange-500 to-orange-600"
        />
        <StatCard
          title="Critical"
          value={criticalAlerts?.total || 0}
          subtitle="严重级别"
          icon={XCircle}
          gradient="from-red-500 to-red-600"
        />
        <StatCard
          title="High"
          value={highAlerts?.total || 0}
          subtitle="高级别"
          icon={AlertCircle}
          gradient="from-amber-500 to-amber-600"
        />
      </div>

      <div className="bg-white rounded-lg shadow">
        {/* 过滤栏 - 分段控件风格 */}
        <div className="p-4 border-b space-y-3">
          <div className="flex gap-3 items-center">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="搜索告警标题或内容..."
              className="flex-1 px-3 py-2 border rounded-md"
              value={filters.keyword}
              onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
            />
            <button
              onClick={() => { setPage(1); refetch(); }}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
            >
              搜索
            </button>
            <button
              onClick={() => setFilters({ status: '', severity: '', sourceId: '', keyword: '', fingerprint: '' })}
              className="px-4 py-2 border rounded-md hover:bg-gray-50 flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              重置
            </button>
          </div>

          <div className="flex gap-2 flex-wrap items-center">
            {/* 聚合模式切换 */}
            <span className="text-sm text-gray-500 py-1.5">视图:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[
                { value: true, label: '聚合' },
                { value: false, label: '列表' },
              ].map(opt => (
                <button
                  key={String(opt.value)}
                  onClick={() => { setAggregateMode(opt.value); setPage(1); }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    aggregateMode === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <span className="text-sm text-gray-500 py-1.5">状态:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[
                { value: '', label: '全部' },
                { value: 'firing', label: '触发中' },
                { value: 'resolved', label: '已恢复' },
                { value: 'suppressed', label: '已抑制' },
                { value: 'acknowledged', label: '已确认' },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => { setFilters({ ...filters, status: opt.value }); setPage(1); }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    filters.status === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <span className="text-sm text-gray-500 py-1.5">级别:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[
                { value: '', label: '全部' },
                { value: 'critical', label: '严重' },
                { value: 'high', label: '重要' },
                { value: 'medium', label: '次要' },
                { value: 'low', label: '提示' },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => { setFilters({ ...filters, severity: opt.value }); setPage(1); }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    filters.severity === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <span className="text-sm text-gray-500 py-1.5">来源:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              <button
                key="all"
                onClick={() => { setFilters({ ...filters, sourceId: '' }); setPage(1); }}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  filters.sourceId === ''
                    ? 'bg-white shadow text-gray-900 font-medium'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                全部
              </button>
              {sources.map(source => (
                <button
                  key={source.id}
                  onClick={() => { setFilters({ ...filters, sourceId: source.id }); setPage(1); }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    filters.sourceId === source.id
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {source.name}
                </button>
              ))}
            </div>

            {/* 指纹搜索 */}
            <div className="flex items-center gap-2 ml-auto">
              <input
                type="text"
                placeholder="搜索指纹..."
                value={filters.fingerprint}
                onChange={(e) => { setFilters({ ...filters, fingerprint: e.target.value }); setPage(1); }}
                className="px-3 py-1 text-sm border rounded-md w-48"
              />
            </div>
          </div>
        </div>

        {/* 告警列表 - 表格布局 */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12">#</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">告警名称</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">级别</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-28">来源</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">命名空间</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">实例</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-40">时间</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">状态</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-gray-500">加载中...</td>
                </tr>
              ) : alerts?.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-gray-500">暂无告警</td>
                </tr>
              ) : aggregateMode ? (
                (alerts?.items as unknown as AlertAggregatedItem[]).map((item, idx) => (
                  <tr
                    key={item.fingerprint}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/alerts/${item.latest.id}`)}
                  >
                    <td className="px-3 py-2 text-sm text-gray-400">{(page - 1) * pageSize + idx + 1}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 truncate max-w-md">{item.latest.title}</span>
                        <span className="flex items-center gap-0.5 text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium">
                          <Fingerprint className="w-3 h-3" />
                          ×{item.count}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5 font-mono">{item.fingerprint}</div>
                    </td>
                    <td className="px-3 py-2"><SeverityBadge severity={item.latest.severity} /></td>
                    <td className="px-3 py-2 text-sm text-gray-500">{item.latest.source}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-32">{getProductDisplayName(item.latest.namespace || '')}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-32">{item.latest.instance_name || item.latest.instance_id || '-'}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 whitespace-nowrap">
                      {item.latest.fired_at ? formatLocalDateTime(item.latest.fired_at) : '-'}
                    </td>
                    <td className="px-3 py-2"><StatusBadge status={item.latest.status} /></td>
                  </tr>
                ))
              ) : (
                alerts?.items.map((alert, idx) => (
                  <tr
                    key={alert.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/alerts/${alert.id}`)}
                  >
                    <td className="px-3 py-2 text-sm text-gray-400">{(page - 1) * pageSize + idx + 1}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 truncate max-w-md">{alert.title}</span>
                        {alert.fire_count > 1 && (
                          <span className="text-xs text-orange-500 font-medium">×{alert.fire_count}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2"><SeverityBadge severity={alert.severity} /></td>
                    <td className="px-3 py-2 text-sm text-gray-500">{alert.source}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-32">{getProductDisplayName(alert.namespace || '')}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-32">{alert.instance_name || alert.instance_id || '-'}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 whitespace-nowrap">
                      {alert.fired_at ? formatLocalDateTime(alert.fired_at) : '-'}
                    </td>
                    <td className="px-3 py-2"><StatusBadge status={alert.status} /></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 紧凑分页 */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t flex items-center justify-between">
            <div className="text-sm text-gray-500">
              共 {alerts?.total} 条，第 {page} / {totalPages} 页
            </div>
            <div className="flex items-center gap-1">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="p-1.5 border rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum: number
                if (totalPages <= 5) {
                  pageNum = i + 1
                } else if (page <= 3) {
                  pageNum = i + 1
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i
                } else {
                  pageNum = page - 2 + i
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`w-8 h-8 text-sm rounded border ${
                      page === pageNum
                        ? 'bg-primary text-white border-primary'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                className="p-1.5 border rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  gradient,
}: {
  title: string
  value: number
  subtitle: string
  icon: React.ComponentType<{ className?: string }>
  gradient: string
}) {
  return (
    <div className={`rounded-xl bg-gradient-to-br ${gradient} p-4 text-white shadow-sm`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-medium opacity-80">{title}</div>
          <div className="text-2xl font-bold mt-0.5">{value.toLocaleString()}</div>
          <div className="text-xs opacity-60 mt-0.5">{subtitle}</div>
        </div>
        <div className="p-2 bg-white/20 rounded-lg">
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
    info: 'bg-gray-100 text-gray-800',
  }

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${styles[severity] || styles.info}`}>
      {severity.toUpperCase()}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    firing: 'bg-red-100 text-red-800',
    resolved: 'bg-green-100 text-green-800',
    suppressed: 'bg-gray-100 text-gray-800',
    acknowledged: 'bg-blue-100 text-blue-800',
  }

  const labels: Record<string, string> = {
    firing: '触发中',
    resolved: '已恢复',
    suppressed: '已抑制',
    acknowledged: '已确认',
  }

  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${styles[status] || styles.firing}`}>
      {labels[status] || status}
    </span>
  )
}
