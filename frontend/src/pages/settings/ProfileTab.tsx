import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { toast } from '@/stores/toast-store'

export function ProfileTab() {
  const { user } = useAuthStore()
  const [formData, setFormData] = useState({
    email: user?.email || '',
  })
  const [saved, setSaved] = useState(false)

  const updateMutation = useMutation({
    mutationFn: (data: { email: string; phone?: string }) =>
      apiClient.put(`/users/${user?.id}`, data),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || '更新失败')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateMutation.mutate(formData)
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-1">个人信息</h3>
      <p className="text-sm text-gray-500 mb-6">管理您的账户信息</p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
          <input
            type="text"
            value={user?.username || ''}
            className="w-full px-3 py-2 border rounded-lg bg-gray-50"
            disabled
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div className="flex items-center gap-4 pt-4 border-t">
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {updateMutation.isPending ? '保存中...' : '保存修改'}
          </button>
          {saved && <span className="text-sm text-green-600">保存成功</span>}
        </div>
      </form>
    </div>
  )
}
