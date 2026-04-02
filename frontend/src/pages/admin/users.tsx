import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { Check, X, Users as UsersIcon } from 'lucide-react'

interface PendingUser {
  id: number
  username: string
  email: string
  phone?: string
  requested_tenant_id?: number
  requested_tenant_name?: string
  created_at: string
}

interface Role {
  id: number
  name: string
  code: string
  tenant_id?: number
  scope?: string
}

export function AdminUsersPage() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const [selectedUser, setSelectedUser] = useState<PendingUser | null>(null)
  const [selectedRole, setSelectedRole] = useState<number | null>(null)
  const [selectedTenant, setSelectedTenant] = useState<number | null>(null)

  // 获取待审批用户
  const { data: pendingUsers = [], isLoading } = useQuery<PendingUser[]>({
    queryKey: ['admin', 'pending-users'],
    queryFn: () => apiClient.get('/admin/users/pending'),
    enabled: user?.is_system === true,
  })

  // 获取角色列表
  const { data: roles = [] } = useQuery<Role[]>({
    queryKey: ['roles'],
    queryFn: () => apiClient.get('/roles'),
    enabled: user?.is_system === true,
  })

  // 审批通过
  const approveMutation = useMutation({
    mutationFn: ({ userId, roleId, tenantId }: { userId: number; roleId: number; tenantId?: number }) =>
      apiClient.post(`/admin/users/${userId}/approve`, { role_id: roleId, tenant_id: tenantId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'pending-users'] })
      setSelectedUser(null)
      setSelectedRole(null)
      setSelectedTenant(null)
    },
  })

  // 拒绝
  const rejectMutation = useMutation({
    mutationFn: (userId: number) =>
      apiClient.post(`/admin/users/${userId}/reject`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'pending-users'] })
    },
  })

  const handleApprove = (user: PendingUser) => {
    setSelectedUser(user)
    setSelectedTenant(user.requested_tenant_id || null)
    setSelectedRole(null)
  }

  const confirmApprove = () => {
    if (!selectedUser || !selectedRole) return
    approveMutation.mutate({
      userId: selectedUser.id,
      roleId: selectedRole,
      tenantId: selectedTenant || undefined,
    })
  }

  const handleReject = (userId: number) => {
    if (confirm('确定要拒绝该用户的注册申请吗？')) {
      rejectMutation.mutate(userId)
    }
  }

  // 获取租户管理员的角色
  const tenantRoles = roles.filter(r => r.tenant_id !== null || r.scope === 'tenant')
  // 获取系统级角色
  const systemRoles = roles.filter(r => r.tenant_id === null && r.scope === 'system')

  if (user?.is_system !== true) {
    return (
      <div className="p-6">
        <div className="bg-red-50 text-red-600 p-4 rounded-lg">
          仅系统管理员可以访问此页面
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">用户管理</h1>
        <p className="text-gray-500 mt-1">系统管理员 - 待审批用户</p>
      </div>

      {isLoading ? (
        <div className="text-center py-8">加载中...</div>
      ) : pendingUsers.length === 0 ? (
        <div className="bg-white rounded-lg shadow-sm p-8 text-center">
          <UsersIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-500">暂无待审批用户</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户名</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">邮箱</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">手机号</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">申请租户</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">注册时间</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {pendingUsers.map((u) => (
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
                        <span className="text-blue-600 font-medium">{u.username[0].toUpperCase()}</span>
                      </div>
                      <span className="font-medium">{u.username}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-500">{u.email}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-500">{u.phone || '-'}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {u.requested_tenant_name ? (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                        {u.requested_tenant_name}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">未指定</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-500 text-sm">
                    {new Date(u.created_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button
                      onClick={() => handleApprove(u)}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700 mr-2"
                    >
                      <Check className="w-4 h-4" />
                      批准
                    </button>
                    <button
                      onClick={() => handleReject(u.id)}
                      disabled={rejectMutation.isPending}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
                    >
                      <X className="w-4 h-4" />
                      拒绝
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 审批 Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-md">
            <div className="p-6 border-b">
              <h2 className="text-xl font-bold">批准用户注册</h2>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-gray-50 p-4 rounded-lg">
                <div className="font-medium">{selectedUser.username}</div>
                <div className="text-sm text-gray-500">{selectedUser.email}</div>
                {selectedUser.requested_tenant_name && (
                  <div className="text-sm text-green-600 mt-1">
                    申请租户: {selectedUser.requested_tenant_name}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">分配角色</label>
                <select
                  value={selectedRole || ''}
                  onChange={(e) => setSelectedRole(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">选择角色</option>
                  <optgroup label="系统级角色">
                    {systemRoles.map((r) => (
                      <option key={r.id} value={r.id}>{r.name}</option>
                    ))}
                  </optgroup>
                  <optgroup label="租户角色">
                    {tenantRoles.map((r) => (
                      <option key={r.id} value={r.id}>{r.name} {r.tenant_id ? `(租户${r.tenant_id})` : ''}</option>
                    ))}
                  </optgroup>
                </select>
              </div>

              {selectedUser.requested_tenant_id && (
                <div className="text-sm text-gray-500">
                  用户将自动加入租户: {selectedUser.requested_tenant_name}
                </div>
              )}

              {approveMutation.error && (
                <div className="text-red-600 text-sm">
                  {approveMutation.error.message || '操作失败'}
                </div>
              )}
            </div>
            <div className="p-6 border-t flex justify-end gap-3">
              <button
                onClick={() => setSelectedUser(null)}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={confirmApprove}
                disabled={!selectedRole || approveMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                {approveMutation.isPending ? '处理中...' : '确认批准'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
