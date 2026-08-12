import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/stores/toast-store'
import { apiClient } from '@/services/api'
import { Modal, DialogFooter } from '@/components/common/Modal'

interface DisposeModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  alertId: number
  onSuccess?: () => void
}

export function DisposeModal({ open, onOpenChange, alertId, onSuccess }: DisposeModalProps) {
  const queryClient = useQueryClient()
  const [comment, setComment] = useState('')

  const disposeMutation = useMutation({
    mutationFn: (data: { action: string; comment: string }) =>
      apiClient.post(`/alerts/${alertId}/dispose`, data),
    onSuccess: () => {
      toast.success('处置记录已添加')
      queryClient.invalidateQueries({ queryKey: ['alert', alertId] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alertStats'] })
      onOpenChange(false)
      setComment('')
      onSuccess?.()
    },
    onError: (error: any) => {
      toast.error(error.message || '添加失败')
    },
  })

  const handleSubmit = () => {
    if (!comment.trim()) {
      toast.warning('请输入处理备注')
      return
    }
    disposeMutation.mutate({ action: 'note', comment: comment.trim() })
  }

  const handleClose = () => {
    onOpenChange(false)
    setComment('')
  }

  return (
    <Modal
      open={open}
      onOpenChange={handleClose}
      title="添加处置记录"
      description="记录当前处理状态和备注信息"
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
            {disposeMutation.isPending ? '处理中...' : '确认添加'}
          </button>
        </DialogFooter>
      }
    >
      <div className="py-2">
        <label className="text-sm font-medium text-gray-700">
          处理备注 <span className="text-red-500">*</span>
        </label>
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="请输入处理备注..."
          rows={4}
          className="w-full mt-2 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
        />
      </div>
    </Modal>
  )
}
