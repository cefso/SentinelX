import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { AlertStats } from '@/types/alert'
import { SeverityBadge } from '@/components/common/Badges'
import { formatLocalDateTime } from '@/utils/datetime'
import { Bell, AlertTriangle, XCircle, AlertCircle, Info, Clock, TrendingUp, Zap } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

// ============ Types ============

interface AlertTrendItem {
  time: string
  count: number
}

interface SourceAlertStats {
  source: string
  source_id: number | null
  source_name: string | null
  total: number
  critical: number
  high: number
}

interface AggregatedAlertItem {
  fingerprint: string
  count: number
  latest: {
    id: number
    title: string
    severity: string
    source: string
    source_name?: string
    fired_at: string
    fingerprint: string
  }
  flapping: boolean
}

// ============ Helpers ============

function formatDuration(firedAt: string): string {
  const diff = Date.now() - new Date(firedAt).getTime()
  const days = Math.floor(diff / 86400000)
  const hours = Math.floor((diff % 86400000) / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)
  if (days > 0) return `${days}天${hours}小时`
  if (hours > 0) return `${hours}小时${minutes}分钟`
  return `${minutes}分钟`
}

function isOver24h(firedAt: string): boolean {
  return Date.now() - new Date(firedAt).getTime() > 86400000
}

// ============ StatCard ============

function StatCard({
  title, value, subtitle, icon: Icon, gradient,
}: {
  title: string
  value: number
  subtitle: string
  icon: React.ComponentType<{ className?: string }>
  gradient: string
}) {
  return (
    <div className={`rounded-xl bg-gradient-to-br ${gradient} p-5 text-white shadow-lg`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm opacity-80">{title}</p>
          <p className="text-3xl font-bold mt-1">{value.toLocaleString()}</p>
          <p className="text-xs opacity-60 mt-1">{subtitle}</p>
        </div>
        <div className="bg-white/20 rounded-lg p-2">
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  )
}

// ============ Main Component ============

export function DashboardPage() {
  const navigate = useNavigate()
  const [trendDays, setTrendDays] = useState(7)
  const [durationFilter, setDurationFilter] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState<string | null>(null)
  const [flappingOnly, setFlappingOnly] = useState(false)

  // Stats
  const { data: stats } = useQuery<AlertStats>({
    queryKey: ['alertStats'],
    queryFn: () => apiClient.get('/alerts/stats'),
  })

  // Trend
  const { data: trendData } = useQuery<{ items: AlertTrendItem[] }>({
    queryKey: ['alertTrend', trendDays],
    queryFn: () => apiClient.get(`/alerts/trend?days=${trendDays}`),
  })

  // By source
  const { data: sourceStats } = useQuery<{ items: SourceAlertStats[] }>({
    queryKey: ['alertStatsBySource'],
    queryFn: () => apiClient.get('/alerts/stats/by-source'),
  })

  // Recent unresolved alerts
  const maxFiredAt = durationFilter
    ? new Date(Date.now() - parseInt(durationFilter) * 3600000).toISOString()
    : undefined

  const { data: recentAlerts } = useQuery<{ items: AggregatedAlertItem[] }>({
    queryKey: ['recentFiringAlerts', maxFiredAt, severityFilter, flappingOnly],
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('status', 'firing')
      params.set('aggregate', 'true')
      params.set('page_size', '10')
      if (maxFiredAt) params.set('max_fired_at', maxFiredAt)
      if (severityFilter) params.set('severity', severityFilter)
      if (flappingOnly) params.set('flapping_only', 'true')
      return apiClient.get(`/alerts?${params.toString()}`)
    },
  })

  const trendItems = trendData?.items || []
  const sourceItems = sourceStats?.items || []
  const alertItems = recentAlerts?.items || []

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex items-center gap-3">
        <TrendingUp className="w-7 h-7 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">未恢复告警 Dashboard</h1>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard title="未恢复总数" value={stats?.firing ?? 0} subtitle="firing 状态" icon={Bell} gradient="from-orange-500 to-orange-600" />
        <StatCard title="严重" value={stats?.critical ?? 0} subtitle="critical" icon={XCircle} gradient="from-red-500 to-red-600" />
        <StatCard title="重要" value={stats?.high ?? 0} subtitle="high" icon={AlertTriangle} gradient="from-amber-500 to-amber-600" />
        <StatCard title="次要" value={stats?.medium ?? 0} subtitle="medium" icon={AlertCircle} gradient="from-yellow-500 to-yellow-600" />
        <StatCard title="提示" value={stats?.low ?? 0} subtitle="low" icon={Info} gradient="from-blue-500 to-blue-600" />
      </div>

      {/* Trend Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">告警趋势</h2>
          <div className="flex gap-1">
            {[
              { label: '1天', value: 1 },
              { label: '7天', value: 7 },
              { label: '30天', value: 30 },
            ].map((opt) => (
              <button
                key={opt.value}
                onClick={() => setTrendDays(opt.value)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  trendDays === opt.value
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={trendItems}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="time"
              tickFormatter={(v) => {
                const d = new Date(v)
                return trendDays === 1
                  ? `${d.getHours()}:00`
                  : `${d.getMonth() + 1}/${d.getDate()}`
              }}
              fontSize={12}
            />
            <YAxis fontSize={12} />
            <Tooltip
              labelFormatter={(v: any) => formatLocalDateTime(v)}
              formatter={(value: any) => [`${value} 条`, '告警数']}
            />
            <Area type="monotone" dataKey="count" stroke="#3b82f6" fill="#93c5fd" fillOpacity={0.6} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Bottom Row: Source Stats + Recent Alerts */}
      <div className="grid grid-cols-3 gap-6">
        {/* Source Stats */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">按告警源统计</h2>
          {sourceItems.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">暂无未恢复告警</p>
          ) : (
            <div className="space-y-3">
              {sourceItems.map((item) => (
                <div key={`${item.source}-${item.source_id}`} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div>
                    <div className="font-medium text-sm text-gray-900">{item.source_name || item.source}</div>
                    <div className="text-xs text-gray-500">{item.source}</div>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    {item.critical > 0 && <span className="text-red-600 font-medium">{item.critical} 严重</span>}
                    {item.high > 0 && <span className="text-amber-600 font-medium">{item.high} 重要</span>}
                    <span className="text-gray-900 font-bold">{item.total}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Unresolved Alerts */}
        <div className="col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">最近未恢复告警</h2>
            <div className="flex gap-2">
              <select
                value={severityFilter || ''}
                onChange={(e) => setSeverityFilter(e.target.value || null)}
                className="px-2 py-1 text-sm border rounded-md"
              >
                <option value="">全部级别</option>
                <option value="critical">严重</option>
                <option value="high">重要</option>
                <option value="medium">次要</option>
                <option value="low">提示</option>
              </select>
              <select
                value={durationFilter || ''}
                onChange={(e) => setDurationFilter(e.target.value || null)}
                className="px-2 py-1 text-sm border rounded-md"
              >
                <option value="">全部时长</option>
                <option value="1">&gt; 1小时</option>
                <option value="6">&gt; 6小时</option>
                <option value="24">&gt; 24小时</option>
                <option value="72">&gt; 3天</option>
                <option value="168">&gt; 7天</option>
              </select>
              <button
                onClick={() => setFlappingOnly(!flappingOnly)}
                className={`px-2 py-1 text-sm rounded-md flex items-center gap-1 transition-colors ${
                  flappingOnly ? 'bg-orange-100 text-orange-700 border border-orange-300' : 'border text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Zap className="w-3 h-3" />
                仅抖动
              </button>
            </div>
          </div>

          {alertItems.length === 0 ? (
            <p className="text-gray-400 text-sm py-8 text-center">暂无符合条件的未恢复告警</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2 font-medium">级别</th>
                    <th className="pb-2 font-medium">告警标题</th>
                    <th className="pb-2 font-medium">告警源</th>
                    <th className="pb-2 font-medium">持续时长</th>
                    <th className="pb-2 font-medium">触发时间</th>
                    <th className="pb-2 font-medium">数量</th>
                  </tr>
                </thead>
                <tbody>
                  {alertItems.map((item) => (
                    <tr
                      key={item.fingerprint}
                      className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                      onClick={() => navigate(`/alerts/${item.latest.id}`)}
                    >
                      <td className="py-2.5"><SeverityBadge severity={item.latest.severity} /></td>
                      <td className="py-2.5 max-w-xs truncate">
                        <div className="flex items-center gap-2">
                          <span className="truncate">{item.latest.title}</span>
                          {item.flapping && (
                            <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 rounded animate-pulse shrink-0">
                              <Zap className="w-3 h-3" />
                              抖动
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 text-gray-600">{item.latest.source_name || item.latest.source}</td>
                      <td className="py-2.5">
                        <span className={`flex items-center gap-1 ${isOver24h(item.latest.fired_at) ? 'text-red-600 font-medium' : 'text-gray-600'}`}>
                          <Clock className="w-3 h-3" />
                          {formatDuration(item.latest.fired_at)}
                        </span>
                      </td>
                      <td className="py-2.5 text-gray-500">{formatLocalDateTime(item.latest.fired_at)}</td>
                      <td className="py-2.5 text-gray-900 font-medium">{item.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
