import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { InstanceAlertGroup, InstanceAlertGroupResponse, InstanceAlertTypeStat } from '@/types/alert'
import { SeverityBadge } from '@/components/common/Badges'
import { formatLocalDateTime } from '@/utils/datetime'
import { Pagination } from '@/components/common/Pagination'
import { Server, Search, RefreshCw, AlertTriangle, ArrowRight } from 'lucide-react'

const PAGE_SIZE = 12

const TYPE_COLORS: Record<string, string> = {
  cpu: 'bg-red-50 text-red-700 border-red-200',
  memory: 'bg-orange-50 text-orange-700 border-orange-200',
  disk: 'bg-amber-50 text-amber-700 border-amber-200',
  process: 'bg-blue-50 text-blue-700 border-blue-200',
  network: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  other: 'bg-gray-50 text-gray-600 border-gray-200',
}

const STATUS_TABS = [
  { value: '', label: '全部' },
  { value: 'firing', label: '未恢复' },
  { value: 'resolved', label: '已恢复' },
  { value: 'suppressed', label: '已抑制' },
] as const

function instanceDisplayName(item: InstanceAlertGroup): string {
  if (item.instance_key === '__unknown__') return '未识别实例'
  return item.instance_name || item.instance_key || '未识别实例'
}

function TypeBadge({
  type,
  instanceKey,
  status,
  ip,
  instanceName,
}: {
  type: InstanceAlertTypeStat
  instanceKey: string
  status: string
  ip?: string | null
  instanceName?: string | null
}) {
  const navigate = useNavigate()
  const color = TYPE_COLORS[type.type] || TYPE_COLORS.other
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        const params = new URLSearchParams()
        params.set('instance_key', instanceKey)
        params.set('type', type.type)
        if (status) params.set('status', status)
        if (ip) params.set('ip', ip)
        if (instanceName) params.set('name', instanceName)
        navigate(`/alerts/by-instance/detail?${params.toString()}`)
      }}
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium hover:opacity-80 transition-opacity ${color}`}
    >
      {type.type_label}
      <span className="font-semibold">{type.count}</span>
    </button>
  )
}

function InstanceCard({ item, status }: { item: InstanceAlertGroup; status: string }) {
  const navigate = useNavigate()
  const displayName = instanceDisplayName(item)
  const detailTo = (() => {
    const params = new URLSearchParams()
    params.set('instance_key', item.instance_key)
    if (status) params.set('status', status)
    if (item.ip) params.set('ip', item.ip)
    if (item.instance_name) params.set('name', item.instance_name)
    return `/alerts/by-instance/detail?${params.toString()}`
  })()

  return (
    <div
      role="link"
      tabIndex={0}
      onClick={() => navigate(detailTo)}
      onKeyDown={(e) => {
        if (e.target !== e.currentTarget) return
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          navigate(detailTo)
        }
      }}
      className="block bg-white rounded-xl border border-border shadow-sm p-4 hover:shadow-md hover:border-primary/30 transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-muted-foreground shrink-0" />
            <h3 className="font-semibold text-foreground truncate" title={displayName}>
              {displayName}
            </h3>
          </div>
          <p className="text-xs text-muted-foreground mt-1 truncate">
            {item.ip ? `IP ${item.ip}` : item.instance_id || '—'}
            {item.sources.length > 0 && ` · ${item.sources.join(', ')}`}
          </p>
        </div>
        {item.max_severity && <SeverityBadge severity={item.max_severity} />}
      </div>

      <div className="mt-3 flex items-center gap-3 text-sm text-muted-foreground">
        <span>
          共 <span className="font-medium text-foreground">{item.alert_count}</span> 条
        </span>
        {item.firing_count > 0 && (
          <span className="text-red-600">
            触发中 {item.firing_count}
          </span>
        )}
        {item.last_fired_at && (
          <span className="ml-auto text-xs">{formatLocalDateTime(item.last_fired_at)}</span>
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5 min-h-[1.5rem]">
        {item.types.map((t) => (
          <TypeBadge
            key={t.type}
            type={t}
            instanceKey={item.instance_key}
            status={status}
            ip={item.ip}
            instanceName={item.instance_name}
          />
        ))}
      </div>
    </div>
  )
}

export function AlertsByInstancePage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [status, setStatus] = useState('')
  const [keyword, setKeyword] = useState('')
  const [searchInput, setSearchInput] = useState('')

  const { data, isLoading, isFetching, refetch } = useQuery<InstanceAlertGroupResponse>({
    queryKey: ['alertsByInstance', page, status, keyword],
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('page_size', String(PAGE_SIZE))
      if (status) params.set('status', status)
      if (keyword) params.set('keyword', keyword)
      return apiClient.get(`/alerts/by-instance?${params.toString()}`)
    },
    placeholderData: (prev) => prev,
  })

  const items = data?.items || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-foreground">实例告警</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            按实例查看告警类型分布（CPU / 内存 / 磁盘等）
            {data?.scanned !== undefined && (
              <span className="ml-2">
                已扫描 {data.scanned} 条
                {data.scan_truncated && (
                  <span className="text-amber-600 ml-1" title="仅统计最近扫描窗口内告警">
                    （窗口截断）
                  </span>
                )}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-md hover:bg-muted transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
            刷新
          </button>
          <button
            onClick={() => navigate('/alerts')}
            className="flex items-center gap-1 text-sm text-primary hover:text-primary/80 transition-colors"
          >
            告警列表
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {data?.scan_truncated && (
        <div className="flex items-center gap-2 px-3 py-2 text-sm bg-amber-50 border border-amber-200 text-amber-800 rounded-md">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          仅统计最近扫描窗口内告警，更早的历史可能未计入。
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-md border overflow-hidden">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => {
                setStatus(tab.value)
                setPage(1)
              }}
              className={`px-3 py-1.5 text-sm transition-colors ${
                status === tab.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-white text-muted-foreground hover:bg-muted'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <form
          className="flex items-center gap-1 ml-auto"
          onSubmit={(e) => {
            e.preventDefault()
            setKeyword(searchInput.trim())
            setPage(1)
          }}
        >
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="搜索实例名 / IP"
              className="pl-8 pr-3 py-1.5 text-sm border rounded-md w-56 focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <button
            type="submit"
            className="px-3 py-1.5 text-sm border rounded-md hover:bg-muted transition-colors"
          >
            搜索
          </button>
        </form>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-36 bg-muted/50 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground">
          <Server className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">暂无符合条件的实例告警</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {items.map((item) => (
            <InstanceCard key={item.instance_key} item={item} status={status} />
          ))}
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} total={total} onPageChange={setPage} />
    </div>
  )
}
