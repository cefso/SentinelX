import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/stores/toast-store'
import { apiClient } from '@/services/api'
import { Modal, DialogFooter } from '@/components/common/Modal'

type DisposeAction = 'note' | 'acknowledge' | 'resolve'

interface DisposeModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  alertId: number
  currentStatus: string
  onSuccess?: () => void
}

const ACTION_OPTIONS: { value: DisposeAction; label: string; description: string }[] = [
  { value: 'note', label: '备注', description: '仅添加处理记录' },
  { value: 'acknowledge', label: '确认', description: '确认告警，状态变为已确认' },
  { value: 'resolve', label: '解决', description: '告警已处理完毕' },
]

export function DisposeModal({ open, onOpenChange, alertId, currentStatus, onSuccess }: DisposeModalProps) {
  const queryClient = useQueryClient()
  const [action, setAction] = useState<DisposeAction>('note')
  const [comment, setComment] = useState('')

  const disposeMutation = useMutation({
    mutationFn: (data: { action: DisposeAction; comment: string }) =>
      apiClient.post(`/alerts/${alertId}/dispose`, data),
    onSuccess: () => {
      toast.success('处置成功')
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alertStats'] })
      onOpenChange(false)
      setComment('')
      setAction('note')
      onSuccess?.()
    },
    onError: (error: any) => {
      toast.error(error.message || '处置失败')
    },
  })

  const handleSubmit = () => {
    if (!comment.trim()) {
      toast.warning('请输入处理备注')
      return
    }
    disposeMutation.mutate({ action, comment: comment.trim() })
  }

  const handleClose = () => {
    onOpenChange(false)
    setComment('')
    setAction('note')
  }

  const getAvailableActions = (): DisposeAction[] => {
    if (currentStatus === 'resolved') {
      return ['note']
    }
    if (currentStatus === 'acknowledged') {
      return ['note', 'resolve']
    }
    return ['note', 'acknowledge', 'resolve']
  }

  const availableActions = getAvailableActions()

  return (
    <Modal
      open={open}
      onOpenChange={handleClose}
      title="处置告警"
      description="选择处置类型并填写处理备注"
      size="sm"
      footer={
        <DialogFooter>
          <button
            onClick={handleClose}
            className="px-4 py-2 border rounded-md hover:bg-gray-50"
            disabled={disposeMutation.isPending}
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={disposeMutation.isPending || !comment.trim()}
            className="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:opacity-50"
          >
            {disposeMutation.isPending ? '处理中...' : '确认处置'}
          </button>
        </DialogFooter>
      }
    >
      <div className="space-y-4 py-2">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">处置类型</label>
          <div className="space-y-2">
            {ACTION_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  action === option.value
                    ? 'border-purple-500 bg-purple-50'
                    : 'border-gray-200 hover:border-gray-300'
                } ${!availableActions.includes(option.value) ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <input
                  type="radio"
                  name="dispose-action"
                  value={option.value}
                  checked={action === option.value}
                  onChange={() => availableActions.includes(option.value) && setAction(option.value)}
                  disabled={!availableActions.includes(option.value)}
                  className="w-4 h-4 text-purple-600 focus:ring-purple-500"
                />
                <div>
                  <div className="text-sm font-medium text-gray-900">{option.label}</div>
                  <div className="text-xs text-gray-500">{option.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            处理备注 <span className="text-red-500">*</span>
          </label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="请输入处理备注..."
            rows={4}
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
          />
        </div>
      </div>
    </Modal>
  )
}
