import { useState } from 'react'
import { Modal, DialogFooter } from '@/components/common/Modal'
import { Download, Calendar } from 'lucide-react'

type ExportRange = 'current_page' | 'all' | 'last_7_days' | 'last_30_days' | 'custom'

interface ExportModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentCount: number
  totalCount: number
  onExport: (range: ExportRange, customDates?: { start: string; end: string }) => void
  isExporting: boolean
}

const EXPORT_OPTIONS: { value: ExportRange; label: string; description: string }[] = [
  { value: 'current_page', label: '当前页', description: '导出当前页面显示的告警' },
  { value: 'all', label: '全部', description: '导出所有符合筛选条件的告警' },
  { value: 'last_7_days', label: '最近 7 天', description: '导出最近 7 天内触发的告警' },
  { value: 'last_30_days', label: '最近 30 天', description: '导出最近 30 天内触发的告警' },
  { value: 'custom', label: '自定义时间', description: '选择起止日期导出' },
]

export function ExportModal({
  open,
  onOpenChange,
  currentCount,
  totalCount,
  onExport,
  isExporting,
}: ExportModalProps) {
  const [selectedRange, setSelectedRange] = useState<ExportRange>('current_page')
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')

  const handleExport = () => {
    if (selectedRange === 'custom') {
      if (!customStart || !customEnd) {
        return
      }
      onExport('custom', { start: customStart, end: customEnd })
    } else {
      onExport(selectedRange)
    }
  }

  const handleClose = () => {
    onOpenChange(false)
    setSelectedRange('current_page')
    setCustomStart('')
    setCustomEnd('')
  }

  const getEstimatedCount = (): string => {
    switch (selectedRange) {
      case 'current_page':
        return `约 ${currentCount} 条`
      case 'all':
        return `约 ${totalCount} 条`
      case 'last_7_days':
      case 'last_30_days':
      case 'custom':
        return '导出时计算'
      default:
        return ''
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={handleClose}
      title="导出告警记录"
      description="选择导出范围，导出为 CSV 格式"
      size="sm"
      footer={
        <DialogFooter>
          <button
            onClick={handleClose}
            className="px-4 py-2 border rounded-md hover:bg-muted"
            disabled={isExporting}
          >
            取消
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting || (selectedRange === 'custom' && (!customStart || !customEnd))}
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
          >
            {isExporting ? (
              <>
                <span className="animate-spin">⏳</span>
                导出中...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                确认导出
              </>
            )}
          </button>
        </DialogFooter>
      }
    >
      <div className="space-y-4 py-2">
        <div className="space-y-2">
          <label className="text-sm font-medium text-foreground">导出范围</label>
          <div className="space-y-2">
            {EXPORT_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedRange === option.value
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-border hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="export-range"
                  value={option.value}
                  checked={selectedRange === option.value}
                  onChange={() => setSelectedRange(option.value)}
                  className="w-4 h-4 text-primary focus:ring-blue-500"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-foreground">{option.label}</div>
                  <div className="text-xs text-muted-foreground">{option.description}</div>
                </div>
                {option.value === selectedRange && (
                  <span className="text-xs text-primary font-medium">{getEstimatedCount()}</span>
                )}
              </label>
            ))}
          </div>
        </div>

        {selectedRange === 'custom' && (
          <div className="space-y-2 p-3 bg-muted rounded-lg">
            <label className="text-sm font-medium text-foreground flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              选择时间范围
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="flex-1 px-3 py-2 border rounded-md text-sm"
                placeholder="开始日期"
              />
              <span className="text-muted-foreground">至</span>
              <input
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="flex-1 px-3 py-2 border rounded-md text-sm"
                placeholder="结束日期"
              />
            </div>
          </div>
        )}

        <div className="text-xs text-muted-foreground bg-muted p-3 rounded-lg">
          <p className="font-medium text-foreground mb-1">导出说明：</p>
          <ul className="list-disc list-inside space-y-0.5">
            <li>导出格式为 CSV，可用 Excel 或 WPS 打开</li>
            <li>包含处置记录列，多条记录用分号分隔</li>
            <li>当前筛选条件（状态、级别、来源）仍然生效</li>
          </ul>
        </div>
      </div>
    </Modal>
  )
}

export type { ExportRange }
