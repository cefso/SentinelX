import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, CloudMetricRecord, CloudProductMetricInput } from '@/services/api'
import { Loader2 } from 'lucide-react'

interface EditModalProps {
  metric: CloudMetricRecord | null
  onClose: () => void
  onSuccess: () => void
}

export function EditModal({ metric, onClose, onSuccess }: EditModalProps) {
  const queryClient = useQueryClient()
  const isEditing = !!metric
  const [formData, setFormData] = useState<CloudProductMetricInput>({
    product: metric?.product || '',
    namespace: metric?.namespace || '',
    metric_name: metric?.metric_name || '',
    metric_desc: metric?.metric_desc || '',
    namespace_desc: metric?.namespace_desc || '',
    metric_name_desc: metric?.metric_name_desc || '',
    unit: metric?.unit || '',
    is_active: metric?.is_active ?? 1,
  })

  const createMutation = useMutation({
    mutationFn: (data: CloudProductMetricInput) => apiClient.createCloudMetric(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cloud-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['cloudMetricsMap'] })
      onSuccess()
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: Partial<CloudProductMetricInput>) => apiClient.updateCloudMetric(metric!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cloud-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['cloudMetricsMap'] })
      onSuccess()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (metric) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-lg max-h-[90vh] overflow-auto">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold">{metric ? '编辑指标' : '创建指标'}</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">命名空间</label>
              <input
                type="text"
                required
                disabled={isEditing}
                value={formData.namespace}
                onChange={(e) => setFormData({ ...formData, namespace: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm bg-gray-50"
                placeholder="如: acs_ecs_dashboard"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">命名空间中文名</label>
              <input
                type="text"
                value={formData.namespace_desc || ''}
                onChange={(e) => setFormData({ ...formData, namespace_desc: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm"
                placeholder="如: 云服务器 ECS"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">指标名称</label>
              <input
                type="text"
                required
                disabled={isEditing}
                value={formData.metric_name}
                onChange={(e) => setFormData({ ...formData, metric_name: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm bg-gray-50"
                placeholder="如: CPUUtilization"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">指标名称中文名</label>
              <input
                type="text"
                value={formData.metric_name_desc || ''}
                onChange={(e) => setFormData({ ...formData, metric_name_desc: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm"
                placeholder="如: CPU 利用率"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">指标描述</label>
            <input
              type="text"
              value={formData.metric_desc || ''}
              onChange={(e) => setFormData({ ...formData, metric_desc: e.target.value })}
              className="w-full px-3 py-2 border rounded-md text-sm"
              placeholder="如: CPU 使用率"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">产品名称</label>
              <input
                type="text"
                required
                disabled={isEditing}
                value={formData.product}
                onChange={(e) => setFormData({ ...formData, product: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm bg-gray-50"
                placeholder="如: 云服务器 ECS"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">单位</label>
              <input
                type="text"
                disabled={isEditing}
                value={formData.unit || ''}
                onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                className="w-full px-3 py-2 border rounded-md text-sm bg-gray-50"
                placeholder="如: %, Count"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">维度</label>
            <input
              type="text"
              disabled={isEditing}
              value={metric?.dimensions?.join(', ') || ''}
              className="w-full px-3 py-2 border rounded-md text-sm bg-gray-50"
              placeholder="如: instanceId, region"
            />
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_active === 1}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked ? 1 : 0 })}
                className="rounded"
              />
              <span className="text-sm">启用</span>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-md hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
            >
              {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {metric ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
