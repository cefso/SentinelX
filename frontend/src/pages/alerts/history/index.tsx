import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { AlertHistoryListResponse } from '@/types/alert'
import { ActionBadge } from '@/components/common/ActionBadge'
import { SeverityBadge, StatusBadge } from '@/components/common/Badges'
import { Pagination } from '@/components/common/Pagination'
import { formatLocalDateTime } from '@/utils/datetime'
import { History, Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const ACTION_OPTIONS = [
  { value: 'all', label: '全部操作' },
  { value: 'received', label: '接入' },
  { value: 'fired', label: '触发' },
  { value: 'filtered', label: '过滤' },
  { value: 'escalated', label: '升级' },
  { value: 'acknowledged', label: '确认' },
  { value: 'resolved', label: '恢复' },
  { value: 'silenced', label: '静默' },
  { value: 'updated', label: '更新' },
]

const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'firing', label: '触发中' },
  { value: 'resolved', label: '已恢复' },
  { value: 'acknowledged', label: '已确认' },
  { value: 'suppressed', label: '已抑制' },
]

export function AlertHistoryPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [action, setAction] = useState('all')
  const [alertStatus, setAlertStatus] = useState('all')
  const [keyword, setKeyword] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')

  const { data, isLoading } = useQuery<AlertHistoryListResponse>({
    queryKey: ['alertHistory', page, pageSize, action, alertStatus, keyword],
    queryFn: () => apiClient.getAlertHistory({
      page,
      page_size: pageSize,
      action: action === 'all' ? undefined : action,
      alert_status: alertStatus === 'all' ? undefined : alertStatus,
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
          <History className="w-6 h-6 text-muted-foreground" />
          <h1 className="text-2xl font-bold text-foreground">告警操作记录</h1>
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="bg-card rounded-lg border shadow-sm p-4">
        <div className="flex flex-wrap gap-4 items-center">
          {/* 搜索框 */}
          <div className="relative flex-1 min-w-[200px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="搜索告警标题..."
              value={searchKeyword}
              onChange={(e) => setSearchKeyword(e.target.value)}
              onKeyDown={handleKeyDown}
              className="pl-9"
            />
          </div>

          {/* 操作类型筛选 */}
          <Select value={action} onValueChange={(v) => { setAction(v); setPage(1) }}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ACTION_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* 告警状态筛选 */}
          <Select value={alertStatus} onValueChange={(v) => { setAlertStatus(v); setPage(1) }}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* 搜索按钮 */}
          <Button onClick={handleSearch}>
            搜索
          </Button>
        </div>
      </div>

      {/* 统计信息 */}
      {data && (
        <div className="text-sm text-muted-foreground">
          共 {data.total} 条记录
        </div>
      )}

      {/* 数据表格 */}
      <div className="bg-card rounded-lg border shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">加载中...</div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">暂无操作记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    时间
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    告警标题
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    级别
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    状态
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    操作类型
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    操作人
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">
                    描述
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.items.map((item) => (
                  <tr key={item.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                      {formatLocalDateTime(item.created_at)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <button
                        onClick={() => navigate(`/alerts/${item.alert_id}`)}
                        className="text-primary hover:text-primary/80 hover:underline truncate max-w-[300px] block text-left"
                        title={item.alert_title}
                      >
                        {item.alert_title || `告警 #${item.alert_id}`}
                      </button>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.alert_severity ? (
                        <SeverityBadge severity={item.alert_severity} />
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {item.alert_status ? (
                        <StatusBadge status={item.alert_status} />
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <ActionBadge action={item.action} />
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                      {item.operator_name || <span className="text-muted-foreground">系统</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground max-w-[200px] truncate" title={item.description || ''}>
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
          <div className="text-sm text-muted-foreground">
            第 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, data.total)} 条，共 {data.total} 条
          </div>
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      )}
    </div>
  )
}
