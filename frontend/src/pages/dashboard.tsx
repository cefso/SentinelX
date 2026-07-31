import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { AlertStats } from '@/types/alert'
import { formatLocalDateTime } from '@/utils/datetime'
import { Bell, AlertTriangle, XCircle, AlertCircle, Info, ArrowRight } from 'lucide-react'
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

  const trendItems = trendData?.items || []
  const sourceItems = sourceStats?.items || []

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">告警看板</h1>
        <p className="text-sm text-gray-500 mt-0.5">未恢复告警统计、趋势分析与异常检测</p>
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

      {/* Bottom Row: Source Stats + Unresolved Summary */}
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

        {/* Unresolved Alerts Summary */}
        <div className="col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">最近未恢复告警</h2>
            <button
              onClick={() => navigate('/alerts/unresolved')}
              className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 transition-colors"
            >
              查看全部
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          <div className="text-center py-6">
            <p className="text-4xl font-bold text-gray-900 mb-2">{stats?.firing ?? 0}</p>
            <p className="text-sm text-gray-500 mb-4">条未恢复告警</p>
            <div className="flex items-center justify-center gap-4 text-sm">
              <span className="text-red-600 font-medium">{stats?.critical ?? 0} 严重</span>
              <span className="text-amber-600 font-medium">{stats?.high ?? 0} 重要</span>
              <span className="text-yellow-600 font-medium">{stats?.medium ?? 0} 次要</span>
              <span className="text-blue-600 font-medium">{stats?.low ?? 0} 提示</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
