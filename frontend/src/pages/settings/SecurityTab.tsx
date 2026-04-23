import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { changePasswordSchema, type ChangePasswordFormData } from '@/schemas'

export function SecurityTab() {
  const { user } = useAuthStore()
  const [saved, setSaved] = useState(false)
  const [serverError, setServerError] = useState('')

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirm_password: '',
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: { old_password: string; new_password: string }) =>
      apiClient.put(`/users/${user?.id}/password`, data),
    onSuccess: () => {
      setSaved(true)
      setServerError('')
      reset()
      setTimeout(() => setSaved(false), 3000)
    },
    onError: (err: any) => {
      setServerError(err.response?.data?.detail || '修改失败')
    },
  })

  const onSubmit = (data: ChangePasswordFormData) => {
    setServerError('')
    updateMutation.mutate({ old_password: data.current_password, new_password: data.new_password })
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-1">安全设置</h3>
      <p className="text-sm text-gray-500 mb-6">管理您的账户安全</p>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">当前密码</label>
          <input
            type="password"
            {...register('current_password')}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {errors.current_password && (
            <p className="mt-1 text-sm text-red-500">{errors.current_password.message}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">新密码</label>
          <input
            type="password"
            {...register('new_password')}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {errors.new_password && (
            <p className="mt-1 text-sm text-red-500">{errors.new_password.message}</p>
          )}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">确认新密码</label>
          <input
            type="password"
            {...register('confirm_password')}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          {errors.confirm_password && (
            <p className="mt-1 text-sm text-red-500">{errors.confirm_password.message}</p>
          )}
        </div>

        {serverError && (
          <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{serverError}</div>
        )}

        {saved && (
          <div className="text-sm text-green-600 bg-green-50 px-3 py-2 rounded">密码修改成功</div>
        )}

        <div className="pt-4 border-t">
          <button
            type="submit"
            disabled={isSubmitting || updateMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {updateMutation.isPending ? '修改中...' : '修改密码'}
          </button>
        </div>
      </form>
    </div>
  )
}
