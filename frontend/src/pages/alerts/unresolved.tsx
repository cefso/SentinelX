import { useState, useCallback, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { SeverityBadge } from '@/components/common/Badges'
import { formatLocalDateTime } from '@/utils/datetime'
import { Clock, Zap, ArrowRight, ChevronDown, ArrowUpDown, LayoutDashboard } from 'lucide-react'

// ============ Types ============

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
  stale: boolean
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

const PAGE_SIZE = 20

// ============ Component ============

export function UnresolvedAlertsPage() {
  const navigate = useNavigate()
  const [durationFilter, setDurationFilter] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState<string | null>(null)
  const [flappingOnly, setFlappingOnly] = useState(false)
  const [staleOnly, setStaleOnly] = useState(false)
  const [sortBy, setSortBy] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [page, setPage] = useState(1)

  const maxFiredAt = durationFilter
    ? new Date(Date.now() - parseInt(durationFilter) * 3600000).toISOString()
    : undefined

  const filterKey = `${maxFiredAt ?? ''}|${severityFilter ?? ''}|${flappingOnly}|${staleOnly}|${sortBy ?? ''}|${sortOrder}`
  const prevFilterKeyRef = useRef(filterKey)
  const accumulatedRef = useRef<AggregatedAlertItem[]>([])

  if (prevFilterKeyRef.current !== filterKey) {
    prevFilterKeyRef.current = filterKey
    accumulatedRef.current = []
  }

  const { data: recentAlerts, isLoading: alertsLoading } = useQuery<{ items: AggregatedAlertItem[]; total: number; alert_total: number }>({
    queryKey: ['recentFiringAlerts', maxFiredAt, severityFilter, flappingOnly, staleOnly, sortBy, sortOrder, page],
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('status', 'firing')
      params.set('aggregate', 'true')
      params.set('page_size', String(PAGE_SIZE))
      params.set('page', String(page))
      if (maxFiredAt) params.set('max_fired_at', maxFiredAt)
      if (severityFilter) params.set('severity', severityFilter)
      if (flappingOnly) params.set('flapping_only', 'true')
      if (staleOnly) params.set('stale_only', 'true')
      if (sortBy) params.set('sort_by', sortBy)
      params.set('sort_order', sortOrder)
      return apiClient.get(`/alerts?${params.toString()}`)
    },
    placeholderData: (prev) => prev,
  })

  useEffect(() => {
    if (recentAlerts?.items) {
      if (page === 1) {
        accumulatedRef.current = recentAlerts.items
      } else {
        const existing = new Set(accumulatedRef.current.map((i) => i.fingerprint))
        const newItems = recentAlerts.items.filter((i) => !existing.has(i.fingerprint))
        if (newItems.length > 0) {
          accumulatedRef.current = [...accumulatedRef.current, ...newItems]
        }
      }
    }
  }, [recentAlerts, page])

  const alertItems = page === 1 ? (recentAlerts?.items || []) : accumulatedRef.current
  const total = recentAlerts?.total || 0
  const alertTotal = recentAlerts?.alert_total || 0
  const hasMore = alertItems.length < total

  const handleLoadMore = useCallback(() => {
    setPage((p) => p + 1)
  }, [])

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">未恢复告警</h1>
          <p className="text-sm text-muted-foreground mt-0.5">共 {alertTotal} 条未恢复告警（{total} 个唯一指纹）</p>
        </div>
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
        >
          <LayoutDashboard className="w-4 h-4" />
          查看告警看板
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <select
          value={severityFilter || ''}
          onChange={(e) => { setSeverityFilter(e.target.value || null); setPage(1) }}
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
          onChange={(e) => { setDurationFilter(e.target.value || null); setPage(1) }}
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
          onClick={() => { setFlappingOnly(!flappingOnly); setPage(1) }}
          className={`px-2 py-1 text-sm rounded-md flex items-center gap-1 transition-colors ${
            flappingOnly ? 'bg-orange-100 text-orange-700 border border-orange-300' : 'border text-gray-600 hover:bg-muted'
          }`}
        >
          <Zap className="w-3 h-3" />
          仅抖动
        </button>
        <button
          onClick={() => { setStaleOnly(!staleOnly); setPage(1) }}
          className={`px-2 py-1 text-sm rounded-md flex items-center gap-1 transition-colors ${
            staleOnly ? 'bg-gray-200 text-gray-700 border border-gray-400' : 'border text-gray-600 hover:bg-muted'
          }`}
        >
          <Clock className="w-3 h-3" />
          仅长时间未更新
        </button>
        <div className="flex items-center gap-1 ml-auto">
          <ArrowUpDown className="w-3 h-3 text-muted-foreground/70" />
          <select
            value={sortBy ? `${sortBy}:${sortOrder}` : ''}
            onChange={(e) => {
              if (!e.target.value) { setSortBy(null); setSortOrder('desc') }
              else {
                const [field, order] = e.target.value.split(':')
                setSortBy(field)
                setSortOrder(order as 'asc' | 'desc')
              }
              setPage(1)
            }}
            className="px-2 py-1 text-sm border rounded-md"
          >
            <option value="">默认排序</option>
            <option value="duration:desc">持续时长 ↓</option>
            <option value="duration:asc">持续时长 ↑</option>
            <option value="severity:asc">严重级别 ↓</option>
            <option value="severity:desc">严重级别 ↑</option>
            <option value="count:desc">告警数量 ↓</option>
            <option value="count:asc">告警数量 ↑</option>
          </select>
        </div>
      </div>

      {/* Table */}
      {alertItems.length === 0 && !alertsLoading ? (
        <p className="text-muted-foreground/70 text-sm py-8 text-center">暂无符合条件的未恢复告警</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground border-b bg-muted">
                <th className="px-4 py-3 font-medium">级别</th>
                <th className="px-4 py-3 font-medium">告警标题</th>
                <th className="px-4 py-3 font-medium">告警源</th>
                <th className="px-4 py-3 font-medium">持续时长</th>
                <th className="px-4 py-3 font-medium">触发时间</th>
                <th className="px-4 py-3 font-medium">数量</th>
              </tr>
            </thead>
            <tbody>
              {alertItems.map((item) => (
                <tr
                  key={item.fingerprint}
                  className="border-b border-gray-50 hover:bg-muted cursor-pointer"
                  onClick={() => navigate(`/alerts/${item.latest.id}`)}
                >
                  <td className="px-4 py-2.5"><SeverityBadge severity={item.latest.severity} /></td>
                  <td className="px-4 py-2.5 max-w-xs truncate">
                    <div className="flex items-center gap-2">
                      <span className="truncate">{item.latest.title}</span>
                      {item.flapping && (
                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 rounded animate-pulse shrink-0">
                          <Zap className="w-3 h-3" />
                          抖动
                        </span>
                      )}
                      {item.stale && (
                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-secondary text-gray-600 rounded shrink-0">
                          <Clock className="w-3 h-3" />
                          长时间未更新
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-gray-600">{item.latest.source_name || item.latest.source}</td>
                  <td className="px-4 py-2.5">
                    <span className={`flex items-center gap-1 ${isOver24h(item.latest.fired_at) ? 'text-red-600 font-medium' : 'text-gray-600'}`}>
                      <Clock className="w-3 h-3" />
                      {formatDuration(item.latest.fired_at)}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">{formatLocalDateTime(item.latest.fired_at)}</td>
                  <td className="px-4 py-2.5 text-foreground font-medium">{item.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Load More */}
      {(alertItems.length > 0 || page > 1) && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground/70">
            已加载 {alertItems.length} / 共 {total} 条
          </span>
          {hasMore && (
            <button
              onClick={handleLoadMore}
              disabled={alertsLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-primary border border-blue-200 rounded-md hover:bg-blue-50 transition-colors disabled:opacity-50"
            >
              <ChevronDown className="w-4 h-4" />
              加载更多
            </button>
          )}
        </div>
      )}
    </div>
  )
}
