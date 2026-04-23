import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { toast } from '@/stores/toast-store'
import { Modal } from '@/components/common/Modal'

export function ApiKeysTab() {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const { data } = useQuery<{ api_keys: any[] }>({
    queryKey: ['apiKeys'],
    queryFn: () => apiClient.get('/auth/api-keys'),
  })
  const apiKeys = data?.api_keys || []

  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => apiClient.delete(`/auth/api-keys/${keyId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['apiKeys'] }),
  })

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-medium mb-1">API Keys</h3>
            <p className="text-sm text-gray-500">用于 Agent 和外部系统认证</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            创建 API Key
          </button>
        </div>

        {apiKeys.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            暂无 API Keys
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-gray-500 border-b">
                <th className="pb-3 font-medium">名称</th>
                <th className="pb-3 font-medium">Key ID</th>
                <th className="pb-3 font-medium">创建时间</th>
                <th className="pb-3 font-medium">过期时间</th>
                <th className="pb-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {apiKeys.map((key: any) => (
                <tr key={key.key_id} className="hover:bg-gray-50">
                  <td className="py-3 font-medium">{key.name}</td>
                  <td className="py-3 font-mono text-sm text-gray-500">{key.key_id}</td>
                  <td className="py-3 text-sm">
                    {key.created_at ? new Date(key.created_at).toLocaleDateString('zh-CN') : '-'}
                  </td>
                  <td className="py-3 text-sm">
                    {key.expires_at ? new Date(key.expires_at).toLocaleDateString('zh-CN') : '永久'}
                  </td>
                  <td className="py-3 text-right">
                    <button
                      onClick={() => {
                        if (confirm(`确定要删除 API Key "${key.name}" 吗？`)) {
                          deleteMutation.mutate(key.key_id)
                        }
                      }}
                      disabled={deleteMutation.isPending}
                      className="text-red-600 hover:text-red-800 text-sm disabled:opacity-50"
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreateModal && (
        <CreateApiKeyModal onClose={() => setShowCreateModal(false)} />
      )}
    </div>
  )
}

function CreateApiKeyModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    name: '',
    expires_days: null as number | null,
  })

  const createMutation = useMutation({
    mutationFn: (data: { name: string; expires_days?: number | null }) =>
      apiClient.post('/auth/api-keys', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] })
      onClose()
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || '创建失败')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      name: formData.name,
      expires_days: formData.expires_days,
    })
  }

  return (
    <Modal
      open={true}
      onOpenChange={(open) => { if (!open) onClose() }}
      title="创建 API Key"
      size="md"
      footer={
        <>
          <button type="button" onClick={onClose} className="px-4 py-2 border rounded-lg hover:bg-gray-50">
            取消
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            form="create-api-key-form"
          >
            创建
          </button>
        </>
      }
    >
      <form id="create-api-key-form" onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">名称</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="如: Production Agent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">有效期（天）</label>
            <input
              type="number"
              min="1"
              value={formData.expires_days || ''}
              onChange={(e) => setFormData({
                ...formData,
                expires_days: e.target.value ? parseInt(e.target.value) : null
              })}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="留空表示永久有效"
            />
          </div>
        </form>
    </Modal>
  )
}
