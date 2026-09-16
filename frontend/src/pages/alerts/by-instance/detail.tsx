import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { AlertListResponse } from '@/types/alert'
import { SeverityBadge, StatusBadge } from '@/components/common/Badges'
import { formatLocalDateTime } from '@/utils/datetime'
import { Pagination } from '@/components/common/Pagination'
import { ArrowLeft, RefreshCw } from 'lucide-react'

const PAGE_SIZE = 20

const TYPE_CHIPS = [
  { value: '', label: '全部类型' },
  { value: 'cpu', label: 'CPU' },
  { value: 'memory', label: '内存' },
  { value: 'disk', label: '磁盘' },
  { value: 'process', label: '进程' },
  { value: 'network', label: '网络' },
  { value: 'other', label: '其他' },
] as const

const STATUS_TABS = [
  { value: '', label: '全部' },
  { value: 'firing', label: '未恢复' },
  { value: 'resolved', label: '已恢复' },
  { value: 'suppressed', label: '已抑制' },
] as const

export function AlertsByInstanceDetailPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const instanceKey = searchParams.get('instance_key') || ''
  const instanceIp = searchParams.get('ip') || ''
  const instanceName = searchParams.get('name') || ''
  const [type, setType] = useState(searchParams.get('type') || '')
  const [status, setStatus] = useState(searchParams.get('status') || '')
  const [page, setPage] = useState(1)

  const updateParams = (next: { type?: string; status?: string }) => {
    const params = new URLSearchParams(searchParams)
    if (next.type !== undefined) {
      if (next.type) params.set('type', next.type)
      else params.delete('type')
    }
    if (next.status !== undefined) {
      if (next.status) params.set('status', next.status)
      else params.delete('status')
    }
    setSearchParams(params, { replace: true })
  }

  const { data, isLoading, isFetching, refetch } = useQuery<AlertListResponse>({
    queryKey: ['alertsByInstanceDetail', instanceKey, type, status, page],
    enabled: !!instanceKey,
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('instance_key', instanceKey)
      params.set('page', String(page))
      params.set('page_size', String(PAGE_SIZE))
      if (type) params.set('type', type)
      if (status) params.set('status', status)
      return apiClient.get(`/alerts/by-instance/alerts?${params.toString()}`)
    },
    placeholderData: (prev) => prev,
  })

  const items = data?.items || []
  const total = data?.total || 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const displayTitle =
    instanceName ||
    (instanceKey === '__unknown__' ? '未识别实例' : instanceKey)

  if (!instanceKey) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">实例告警明细</h1>
        <p className="text-sm text-muted-foreground">缺少实例参数，请从实例列表进入。</p>
        <Link to="/alerts/by-instance" className="text-sm text-primary inline-flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" />
          返回实例告警
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <button
            onClick={() => navigate('/alerts/by-instance')}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            返回实例告警
          </button>
          <h1 className="text-2xl font-bold text-foreground break-all">{displayTitle}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {[
              instanceIp ? `IP ${instanceIp}` : null,
              instanceName && instanceName !== instanceKey ? instanceKey : null,
              `共 ${total} 条告警`,
              type && TYPE_CHIPS.find((c) => c.value === type)
                ? TYPE_CHIPS.find((c) => c.value === type)!.label
                : null,
            ]
              .filter(Boolean)
              .join(' · ')}
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1 px-3 py-1.5 text-sm border rounded-md hover:bg-muted transition-colors mt-8"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap gap-1.5">
          {TYPE_CHIPS.map((chip) => (
            <button
              key={chip.value}
              onClick={() => {
                setType(chip.value)
                setPage(1)
                updateParams({ type: chip.value })
              }}
              className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                type === chip.value
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-white text-muted-foreground hover:bg-muted'
              }`}
            >
              {chip.label}
            </button>
          ))}
        </div>
        <div className="flex rounded-md border overflow-hidden ml-auto">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => {
                setStatus(tab.value)
                setPage(1)
                updateParams({ status: tab.value })
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
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 bg-muted/50 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-muted-foreground/70 text-sm py-12 text-center">暂无符合条件的告警</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-left text-muted-foreground">
                <th className="px-4 py-3 font-medium">告警标题</th>
                <th className="px-4 py-3 font-medium">级别</th>
                <th className="px-4 py-3 font-medium">状态</th>
                <th className="px-4 py-3 font-medium">指标</th>
                <th className="px-4 py-3 font-medium">触发时间</th>
                <th className="px-4 py-3 font-medium">来源</th>
              </tr>
            </thead>
            <tbody>
              {items.map((alert) => (
                <tr
                  key={alert.id}
                  className="border-b last:border-0 hover:bg-muted/30 cursor-pointer"
                  onClick={() => navigate(`/alerts/${alert.id}`)}
                >
                  <td className="px-4 py-3 max-w-md">
                    <div className="truncate font-medium text-foreground" title={alert.title}>
                      {alert.title}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <SeverityBadge severity={alert.severity} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={alert.status} />
                  </td>
                  <td className="px-4 py-3 text-muted-foreground truncate max-w-32">
                    {alert.metric_name || '-'}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                    {formatLocalDateTime(alert.fired_at)}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {alert.source_name || alert.source}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={page} totalPages={totalPages} total={total} onPageChange={setPage} />
    </div>
  )
}
