import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import type { WebhookLogsResponse } from '@/services/api'
import { Modal } from '@/components/common/Modal'
import { ScrollText } from 'lucide-react'

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

export function WebhookLogModal({ open, onOpenChange }: WebhookLogModalProps) {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery<WebhookLogsResponse>({
    queryKey: ['webhook-logs', page],
    queryFn: () => apiClient.getWebhookLogs({ page, page_size: 20, dismissed: false }),
    enabled: open,
  })

  const dismissMutation = useMutation({
    mutationFn: (params: { id?: number; dismiss_all?: boolean }) =>
      apiClient.dismissWebhookLogs(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhook-logs'] })
      queryClient.invalidateQueries({ queryKey: ['webhook-logs-count'] })
      setSelectedId(null)
    },
  })

  const logs = data?.items || []
  const selectedLog = logs.find((log) => log.id === selectedId) || logs[0]

  useEffect(() => {
    if (logs.length > 0 && !selectedId) {
      setSelectedId(logs[0].id)
    }
  }, [logs, selectedId])

  const handleDismissCurrent = () => {
    if (selectedLog) {
      dismissMutation.mutate({ id: selectedLog.id })
    }
  }

  const handleDismissAll = () => {
    dismissMutation.mutate({ dismiss_all: true })
  }

  const formatDate = (dateString?: string) => {
    if (!dateString) return '-'
    try {
      return new Date(dateString).toLocaleString()
    } catch {
      return dateString
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={`Webhook 接收日志 (${data?.total || 0})`}
      size="xl"
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : logs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-gray-500">
          <ScrollText className="w-12 h-12 mb-4 text-gray-300" />
          <p>暂无 Webhook 日志</p>
        </div>
      ) : (
        <>
          {/* 操作栏 */}
          <div className="flex items-center gap-4 mb-4">
            <div className="flex-1">
              <select
                value={selectedLog?.id || ''}
                onChange={(e) => setSelectedId(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {logs.map((log) => (
                  <option key={log.id} value={log.id}>
                    {formatDate(log.created_at)} - {log.source_type} - {statusLabels[log.status] || log.status}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handleDismissCurrent}
              disabled={!selectedLog || dismissMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 disabled:opacity-50"
            >
              {dismissMutation.isPending ? '处理中...' : '忽略当前'}
            </button>
            <button
              onClick={handleDismissAll}
              disabled={dismissMutation.isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-lg hover:bg-orange-700 disabled:opacity-50"
            >
              {dismissMutation.isPending ? '处理中...' : '忽略全部'}
            </button>
          </div>

          {/* 详情卡片 */}
          {selectedLog && (
            <div className="border rounded-lg p-4 space-y-4 overflow-y-auto max-h-[50vh]">
              {/* 基本信息 */}
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">时间:</span>
                  <span className="font-medium">{formatDate(selectedLog.created_at)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">来源:</span>
                  <span className="font-medium">{selectedLog.source_type}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">状态:</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColors[selectedLog.status] || ''}`}>
                    {statusLabels[selectedLog.status] || selectedLog.status}
                  </span>
                </div>
              </div>

              {/* 原始数据 */}
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">原始数据</h4>
                <pre className="p-3 bg-gray-50 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap max-h-64">
                  {JSON.stringify(selectedLog.raw_data, null, 2)}
                </pre>
              </div>

              {/* 错误详情 */}
              {selectedLog.error_message && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">错误详情</h4>
                  <pre className="p-3 bg-red-50 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap max-h-48 text-red-800">
                    {selectedLog.error_message}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* 分页 */}
          {data && data.total > 20 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <span className="text-sm text-gray-500">
                共 {data.total} 条，第 {page} / {Math.ceil(data.total / 20)} 页
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  上一页
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= Math.ceil(data.total / 20)}
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-50"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </Modal>
  )
}
