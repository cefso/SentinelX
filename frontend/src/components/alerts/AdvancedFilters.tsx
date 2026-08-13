import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

export interface AdvancedFilterState {
  startTime: string
  endTime: string
  maxFiredAt: string
  flappingOnly: boolean
  staleOnly: boolean
  assigneeId: '' | number
}

interface AdvancedFiltersProps {
  filters: AdvancedFilterState
  onFilterChange: (filters: AdvancedFilterState) => void
  users: { id: number; username: string }[]
}

const timeRangeOptions = [
  { value: '', label: '全部时间' },
  { value: '1h', label: '最近1小时' },
  { value: '24h', label: '最近24小时' },
  { value: '7d', label: '最近7天' },
]

const durationOptions = [
  { value: '', label: '不限' },
  { value: '1h', label: '超过1小时' },
  { value: '6h', label: '超过6小时' },
  { value: '24h', label: '超过24小时' },
]

function getTimeRange(value: string): { start_time?: string } {
  if (!value) return {}
  const now = new Date()
  const start = new Date()
  switch (value) {
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
}

function getDurationValue(value: string): { max_fired_at?: string } {
  if (!value) return {}
  const now = new Date()
  const threshold = new Date()
  switch (value) {
    case '1h':
      threshold.setHours(now.getHours() - 1)
      break
    case '6h':
      threshold.setHours(now.getHours() - 6)
      break
    case '24h':
      threshold.setDate(now.getDate() - 1)
      break
  }
  return { max_fired_at: threshold.toISOString() }
}

export function AdvancedFilters({
  filters,
  onFilterChange,
  users,
}: AdvancedFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  // 计算当前选中的时间范围值
  const selectedTimeRange = filters.startTime ? getTimeRangeValue(filters.startTime) : ''
  const selectedDuration = filters.maxFiredAt ? getDurationValue2(filters.maxFiredAt) : ''

  const activeFilterCount = [
    filters.startTime,
    filters.maxFiredAt,
    filters.flappingOnly,
    filters.staleOnly,
    filters.assigneeId,
  ].filter(Boolean).length

  return (
    <div className="border rounded-lg bg-gray-50">
      {/* 折叠头 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2 hover:bg-gray-100 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700">高级筛选</span>
          {activeFilterCount > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium text-white bg-blue-500 rounded-full">
              {activeFilterCount}
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-500" />
        )}
      </button>

      {/* 展开内容 */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t">
          {/* 时间范围 */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-600">时间范围</label>
            <div className="flex gap-1 bg-gray-200 p-1 rounded-lg">
              {timeRangeOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => {
                    const range = getTimeRange(opt.value)
                    onFilterChange({
                      ...filters,
                      startTime: range.start_time || '',
                    })
                  }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    selectedTimeRange === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 持续时长筛选 */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">持续时长</label>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {durationOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => {
                    const duration = getDurationValue(opt.value)
                    onFilterChange({
                      ...filters,
                      maxFiredAt: duration.max_fired_at || '',
                    })
                  }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    selectedDuration === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 特殊状态筛选 */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">特殊状态</label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.flappingOnly}
                  onChange={(e) => onFilterChange({ ...filters, flappingOnly: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">抖动告警</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.staleOnly}
                  onChange={(e) => onFilterChange({ ...filters, staleOnly: e.target.checked })}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">长时间未更新</span>
              </label>
            </div>
          </div>

          {/* 处理人筛选 */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">处理人</label>
            <select
              value={filters.assigneeId}
              onChange={(e) => onFilterChange({
                ...filters,
                assigneeId: e.target.value ? Number(e.target.value) : '',
              })}
              className="w-full max-w-xs px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">全部处理人</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>{user.username}</option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  )
}

// 辅助函数：从 ISO 时间字符串反推选择的值
function getTimeRangeValue(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)

  if (diffHours <= 1.5) return '1h'
  if (diffHours <= 25) return '24h'
  if (diffHours <= 169) return '7d'
  return ''
}

function getDurationValue2(isoString: string): string {
  const date = new Date(isoString)
  const now = new Date()
  const diffHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)

  if (diffHours <= 1.5) return '1h'
  if (diffHours <= 6.5) return '6h'
  if (diffHours <= 25) return '24h'
  return ''
}
