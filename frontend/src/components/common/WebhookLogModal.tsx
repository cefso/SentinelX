import { useState, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import type { WebhookLogsResponse, WebhookLog } from '@/services/api'
import { Modal } from '@/components/common/Modal'
import { ScrollText, Search, RotateCcw, ChevronLeft, ChevronRight, Square, CheckSquare } from 'lucide-react'

interface WebhookLogModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const statusLabels: Record<string, string> = {
  success: '成功',
  parse_error: '解析失败',
  format_error: '格式错误',
  server_error: '服务器错误',
}

const statusColors: Record<string, string> = {
  success: 'text-green-600 bg-green-50',
  parse_error: 'text-red-600 bg-red-50',
  format_error: 'text-orange-600 bg-orange-50',
  server_error: 'text-red-600 bg-red-50',
}

const statusOptions = [
  { value: '', label: '全部状态' },
  { value: 'success', label: '成功' },
  { value: 'parse_error', label: '解析失败' },
  { value: 'format_error', label: '格式错误' },
  { value: 'server_error', label: '服务器错误' },
]

const timeOptions = [
  { value: '', label: '全部时间' },
  { value: '1h', label: '最近1小时' },
  { value: '24h', label: '最近24小时' },
  { value: '7d', label: '最近7天' },
]

export function WebhookLogModal({ open, onOpenChange }: WebhookLogModalProps) {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [sourceFilter] = useState('')
  const [timeFilter, setTimeFilter] = useState('')
  const [keyword, setKeyword] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [expandedId, setExpandedId] = useState<number | null>(null)

  // 计算时间范围
  const timeRange = useMemo(() => {
    if (!timeFilter) return {}
    const now = new Date()
    const start = new Date()
    switch (timeFilter) {
      case '1h':
        start.setHours(now.getHours() - 1)
        break
      case '24h':
        start.setDate(now.getDate() - 1)
        break
      case '7d':
        start.setDate(now.getDate() - 7)
        break
    }
    return { start_time: start.toISOString() }
  }, [timeFilter])

  const { data, isLoading, refetch } = useQuery<WebhookLogsResponse>({
    queryKey: ['webhook-logs', page, statusFilter, sourceFilter, timeFilter],
    queryFn: () => apiClient.getWebhookLogs({
      page,
      page_size: 20,
      dismissed: false,
      status: statusFilter || undefined,
      source_type: sourceFilter || undefined,
      ...timeRange,
    }),
    enabled: open,
  })

  const dismissMutation = useMutation({
    mutationFn: (params: { id?: number; ids?: number[]; dismiss_all?: boolean }) =>
      apiClient.dismissWebhookLogs(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhook-logs'] })
      queryClient.invalidateQueries({ queryKey: ['webhook-logs-count'] })
      setSelectedIds(new Set())
      setExpandedId(null)
    },
  })

  const logs = data?.items || []
  const totalPages = Math.ceil((data?.total || 0) / 20)

  // 筛选后的日志（关键词搜索在前端进行）
  const filteredLogs = useMemo(() => {
    if (!keyword) return logs
    const lowerKeyword = keyword.toLowerCase()
    return logs.filter(log => {
      const rawStr = JSON.stringify(log.raw_data).toLowerCase()
      return rawStr.includes(lowerKeyword) ||
             log.source_type.toLowerCase().includes(lowerKeyword) ||
             (log.error_message && log.error_message.toLowerCase().includes(lowerKeyword))
    })
  }, [logs, keyword])

  // 重置分页当筛选条件改变时
  useEffect(() => {
    setPage(1)
    setSelectedIds(new Set())
  }, [statusFilter, sourceFilter, timeFilter])

  const handleSelectAll = () => {
    if (selectedIds.size === filteredLogs.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredLogs.map(log => log.id)))
    }
  }

  const handleSelectOne = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const handleDismissSelected = () => {
    if (selectedIds.size === 0) return
    dismissMutation.mutate({ ids: Array.from(selectedIds) })
  }

  const handleDismissAll = () => {
    dismissMutation.mutate({ dismiss_all: true })
  }

  const handleDismissSingle = (id: number) => {
    dismissMutation.mutate({ id })
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-'
    try {
      return new Date(dateString).toLocaleString()
    } catch {
      return dateString
    }
  }

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id)
  }

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={`Webhook 接收日志 (${data?.total || 0})`}
      size="full"
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          {/* 筛选栏 */}
          <div className="flex flex-wrap gap-3 mb-4">
            {/* 搜索框 */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground/70" />
              <input
                type="text"
                placeholder="搜索日志内容..."
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                className="w-full pl-10 pr-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* 状态筛选 */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {statusOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            {/* 时间筛选 */}
            <select
              value={timeFilter}
              onChange={(e) => setTimeFilter(e.target.value)}
              className="px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {timeOptions.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            {/* 刷新按钮 */}
            <button
              onClick={() => refetch()}
              className="px-3 py-2 border rounded-lg hover:bg-muted flex items-center gap-1"
              title="刷新"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          {filteredLogs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <ScrollText className="w-12 h-12 mb-4 text-gray-300" />
              <p>暂无 Webhook 日志</p>
            </div>
          ) : (
            <>
              {/* 表格 */}
              <div className="border rounded-lg overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-muted">
                    <tr>
                      <th className="w-10 px-3 py-3">
                        <button onClick={handleSelectAll} className="flex items-center justify-center">
                          {selectedIds.size === filteredLogs.length && filteredLogs.length > 0 ? (
                            <CheckSquare className="w-4 h-4 text-primary" />
                          ) : (
                            <Square className="w-4 h-4 text-muted-foreground/70" />
                          )}
                        </button>
                      </th>
                      <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase">时间</th>
                      <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase">来源</th>
                      <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase">状态</th>
                      <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase">告警ID</th>
                      <th className="px-3 py-3 text-right text-xs font-medium text-muted-foreground uppercase">操作</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {filteredLogs.map((log) => (
                      <LogRow
                        key={log.id}
                        log={log}
                        isSelected={selectedIds.has(log.id)}
                        isExpanded={expandedId === log.id}
                        onSelect={() => handleSelectOne(log.id)}
                        onToggleExpand={() => toggleExpand(log.id)}
                        onDismiss={() => handleDismissSingle(log.id)}
                        formatDate={formatDate}
                        isDismissing={dismissMutation.isPending}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 底部操作栏 */}
              <div className="flex items-center justify-between mt-4 pt-4 border-t">
                <div className="flex items-center gap-4">
                  {selectedIds.size > 0 && (
                    <button
                      onClick={handleDismissSelected}
                      disabled={dismissMutation.isPending}
                      className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-lg hover:bg-orange-700 disabled:opacity-50"
                    >
                      {dismissMutation.isPending ? '处理中...' : `忽略选中 (${selectedIds.size})`}
                    </button>
                  )}
                  <button
                    onClick={handleDismissAll}
                    disabled={dismissMutation.isPending}
                    className="px-4 py-2 text-sm font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 disabled:opacity-50"
                  >
                    {dismissMutation.isPending ? '处理中...' : '忽略全部'}
                  </button>
                </div>

                {/* 分页 */}
                {totalPages > 1 && (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      共 {data?.total || 0} 条，第 {page} / {totalPages} 页
                    </span>
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-1.5 border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
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
                              ? 'bg-primary text-white border-blue-500'
                              : 'hover:bg-muted'
                          }`}
                        >
                          {pageNum}
                        </button>
                      )
                    })}
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page >= totalPages}
                      className="p-1.5 border rounded hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </>
      )}
    </Modal>
  )
}

// 日志行组件
function LogRow({
  log,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpand,
  onDismiss,
  formatDate,
  isDismissing,
}: {
  log: WebhookLog
  isSelected: boolean
  isExpanded: boolean
  onSelect: () => void
  onToggleExpand: () => void
  onDismiss: () => void
  formatDate: (date?: string) => string
  isDismissing: boolean
}) {
  return (
    <>
      <tr
        className={`hover:bg-muted cursor-pointer ${isSelected ? 'bg-blue-50' : ''}`}
        onClick={onToggleExpand}
      >
        <td className="px-3 py-3" onClick={(e) => e.stopPropagation()}>
          <button onClick={onSelect} className="flex items-center justify-center">
            {isSelected ? (
              <CheckSquare className="w-4 h-4 text-primary" />
            ) : (
              <Square className="w-4 h-4 text-muted-foreground/70" />
            )}
          </button>
        </td>
        <td className="px-3 py-3 text-sm text-foreground whitespace-nowrap">
          {formatDate(log.created_at)}
        </td>
        <td className="px-3 py-3 text-sm text-muted-foreground">
          {log.source_type}
        </td>
        <td className="px-3 py-3">
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColors[log.status] || ''}`}>
            {statusLabels[log.status] || log.status}
          </span>
        </td>
        <td className="px-3 py-3 text-sm text-muted-foreground">
          {log.alert_id || '-'}
        </td>
        <td className="px-3 py-3 text-right" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={onDismiss}
            disabled={isDismissing}
            className="text-sm text-orange-600 hover:text-orange-800 disabled:opacity-50"
          >
            忽略
          </button>
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={6} className="px-3 py-3 bg-muted">
            <div className="space-y-3">
              {/* 原始数据 */}
              <div>
                <h4 className="text-xs font-medium text-muted-foreground mb-1">原始数据</h4>
                <pre className="p-3 bg-white border rounded-lg text-xs overflow-x-auto whitespace-pre-wrap max-h-48">
                  {JSON.stringify(log.raw_data, null, 2)}
                </pre>
              </div>
              {/* 错误详情 */}
              {log.error_message && (
                <div>
                  <h4 className="text-xs font-medium text-muted-foreground mb-1">错误详情</h4>
                  <pre className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap max-h-32 text-red-800">
                    {log.error_message}
                  </pre>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
