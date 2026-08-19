import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { AlertHistoryListResponse } from '@/types/alert'
import { ActionBadge } from '@/components/common/ActionBadge'
import { SeverityBadge, StatusBadge } from '@/components/common/Badges'
import { formatLocalDateTime } from '@/utils/datetime'
import { History, Search, ChevronLeft, ChevronRight } from 'lucide-react'

const ACTION_OPTIONS = [
  { value: '', label: '全部操作' },
  { value: 'fired', label: '触发' },
  { value: 'resolved', label: '恢复' },
  { value: 'deduplicated', label: '去重' },
  { value: 'aggregated', label: '聚合' },
  { value: 'dispose_note', label: '备注' },
  { value: 'dispose_acknowledge', label: '确认' },
  { value: 'dispose_resolve', label: '解决' },
  { value: 'dispose_silence', label: '静默' },
  { value: 'acknowledge_callback', label: '外部确认' },
  { value: 'resolve_callback', label: '外部恢复' },
  { value: 'silence_callback', label: '外部静默' },
  { value: 'auto_assign', label: '自动分配' },
  { value: 'update', label: '更新' },
]

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'firing', label: '触发中' },
  { value: 'resolved', label: '已恢复' },
  { value: 'acknowledged', label: '已确认' },
  { value: 'suppressed', label: '已抑制' },
]

export function AlertHistoryPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [action, setAction] = useState('')
  const [alertStatus, setAlertStatus] = useState('')
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')

  const { data, isLoading } = useQuery<AlertHistoryListResponse>({
    queryKey: ['alertHistory', page, pageSize, action, alertStatus, keyword],
    queryFn: () => apiClient.getAlertHistory({
      page,
      page_size: pageSize,
      action: action || undefined,
      alert_status: alertStatus || undefined,
      keyword: keyword || undefined,
    }),
  })

  const handleSearch = () => {
    setPage(1)
    setKeyword(searchKeyword)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <History className="w-6 h-6 text-gray-500" />
          <h1 className="text-2xl font-bold text-gray-900">告警操作记录</h1>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex flex-wrap gap-4 items-center">
          {/* 搜索框 */}
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="搜索告警标题..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {/* 操作类型筛选 */}
          <select
            value={action}
            onChange={(e) => { setAction(e.target.value); setPage(1) }}
            className="px-3 py-2 border rounded-lg text-sm"
          >
            {ACTION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {/* 告警状态筛选 */}
          <select
            value={alertStatus}
            onChange={(e) => { setAlertStatus(e.target.value); setPage(1) }}
            className="px-3 py-2 border rounded-lg text-sm"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {/* 搜索按钮 */}
          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            搜索
          </button>
        </div>
      </div>

      {/* 统计信息 */}
      {data && (
        <div className="text-sm text-gray-500">
          共 {data.total} 条记录
        </div>
      )}

      {/* 数据表格 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-8 text-center text-gray-500">暂无操作记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    时间
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    告警标题
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    级别
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作类型
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    操作人
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    描述
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {data.items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                      {formatLocalDateTime(item.created_at)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <button
                        onClick={() => navigate(`/alerts/${item.alert_id}`)}
                        className="text-blue-600 hover:text-blue-700 hover:underline truncate max-w-[300px] block"
                        title={item.alert_title}
                      >
                        {item.alert_title || `告警 #${item.alert_id}`}
                      </button>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.alert_severity ? (
                        <SeverityBadge severity={item.alert_severity} />
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.alert_status ? (
                        <StatusBadge status={item.alert_status} />
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <ActionBadge action={item.action} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                      {item.operator_name || <span className="text-gray-400">系统</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate" title={item.description || ''}>
                      {item.description || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 分页 */}
      {data && data.total > pageSize && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-gray-500">
            第 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, data.total)} 条，共 {data.total} 条
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-gray-700">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
