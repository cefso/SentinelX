import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'

export function SecurityTab() {
  const { user } = useAuthStore()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const updateMutation = useMutation({
    mutationFn: (data: { old_password: string; new_password: string }) =>
      apiClient.put(`/users/${user?.id}/password`, data),
    onSuccess: () => {
      setSaved(true)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setError('')
      setTimeout(() => setSaved(false), 3000)
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || '修改失败')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (newPassword !== confirmPassword) {
      setError('新密码与确认密码不匹配')
      return
    }

    if (newPassword.length < 8) {
      setError('密码长度至少8位')
      return
    }

    updateMutation.mutate({ old_password: currentPassword, new_password: newPassword })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-1">安全设置</h3>
      <p className="text-sm text-gray-500 mb-6">管理您的账户安全</p>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">新密码</label>
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
            minLength={8}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>

        {error && (
          <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</div>
        )}

        {saved && (
          <div className="text-sm text-green-600 bg-green-50 px-3 py-2 rounded">密码修改成功</div>
        )}

        <div className="pt-4 border-t">
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {updateMutation.isPending ? '修改中...' : '修改密码'}
          </button>
        </div>
      </form>
    </div>
  )
}
