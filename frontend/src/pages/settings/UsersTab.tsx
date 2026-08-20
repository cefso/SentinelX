import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { Plus, Check, X, RotateCcw } from 'lucide-react'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

interface Role {
  id: number
  name: string
  code: string
  tenant_id?: number
  scope?: string
}

interface Tenant {
  id: number
  name: string
  slug: string
  max_alerts: number
  max_users: number
  max_rules: number
  max_channels: number
  alert_qps: number
  is_active: boolean
  config: Record<string, any>
}

interface UserItem {
  id: number
  username: string
  email: string
  phone?: string
  is_superuser: boolean
  is_active: boolean
  is_approved: boolean
  role_id?: number
  created_at: string
}

export function UsersTab() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingUser, setEditingUser] = useState<UserItem | null>(null)

  // 租户管理员或系统管理员可以管理用户
  const canManageUsers = user?.is_superuser === true || user?.is_system === true

  const { data: users = [] } = useQuery<UserItem[]>({
    queryKey: ['users'],
    queryFn: () => apiClient.get('/users'),
  })

  const { data: roles = [] } = useQuery<Role[]>({
    queryKey: ['roles'],
    queryFn: () => apiClient.get('/roles'),
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiClient.post(`/users/${id}/activate?is_active=${is_active}`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const removeUserMutation = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/users/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  const resetPermissionsMutation = useMutation({
    mutationFn: (id: number) => apiClient.post(`/users/${id}/reset-permissions`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  return (
    <div className="space-y-6">
      <div className="bg-card rounded-xl shadow-sm border p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-medium mb-1">用户管理</h3>
            <p className="text-sm text-muted-foreground">管理租户内的用户账户</p>
          </div>
          {canManageUsers && (
            <Button onClick={() => setShowCreateModal(true)} className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              添加用户
            </Button>
          )}
        </div>

        {users.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            暂无用户
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-muted-foreground border-b">
                  <th className="pb-3 font-medium">用户名</th>
                  <th className="pb-3 font-medium">邮箱</th>
                  <th className="pb-3 font-medium">手机号</th>
                  <th className="pb-3 font-medium">角色</th>
                  <th className="pb-3 font-medium">状态</th>
                  {canManageUsers && <th className="pb-3 font-medium text-right">操作</th>}
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-muted/50">
                    <td className="py-3 font-medium">{u.username}</td>
                    <td className="py-3 text-sm text-muted-foreground">{u.email}</td>
                    <td className="py-3 text-sm text-muted-foreground">{u.phone || '-'}</td>
                    <td className="py-3">
                      <span className={cn(
                        "px-2 py-1 text-xs rounded",
                        u.is_superuser ? 'bg-purple-100 text-purple-800' : 'bg-secondary text-secondary-foreground'
                      )}>
                        {u.is_superuser ? '管理员' : '用户'}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={cn(
                        "px-2 py-1 text-xs rounded",
                        u.is_active ? 'bg-green-100 text-green-800' : 'bg-destructive/10 text-destructive'
                      )}>
                        {u.is_active ? '活跃' : '禁用'}
                      </span>
                    </td>
                    {canManageUsers && (
                      <td className="py-3 text-right">
                        <button
                          onClick={() => setEditingUser(u)}
                          disabled={u.id === user?.id}
                          className="px-2 py-1 text-xs bg-primary/10 text-primary rounded hover:bg-primary/20 mr-2 disabled:opacity-50"
                        >
                          调整权限
                        </button>
                        <button
                          onClick={() => toggleActiveMutation.mutate({ id: u.id, is_active: !u.is_active })}
                          disabled={toggleActiveMutation.isPending || u.id === user?.id}
                          className={cn(
                            "px-2 py-1 text-xs rounded mr-2 transition-colors disabled:opacity-50",
                            u.is_active
                              ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                              : 'bg-green-100 text-green-800 hover:bg-green-200'
                          )}
                        >
                          {u.is_active ? '禁用' : '启用'}
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`确定要重置用户 ${u.username} 的权限吗？这将删除该用户的所有租户关联。`)) {
                              resetPermissionsMutation.mutate(u.id)
                            }
                          }}
                          disabled={resetPermissionsMutation.isPending || u.id === user?.id}
                          className="px-2 py-1 text-xs bg-orange-100 text-orange-800 rounded hover:bg-orange-200 mr-2 disabled:opacity-50"
                          title="重置权限"
                        >
                          <RotateCcw className="w-3 h-3 inline mr-1" />
                          重置
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`确定要从本租户移除用户 ${u.username} 吗？`)) {
                              removeUserMutation.mutate(u.id)
                            }
                          }}
                          disabled={removeUserMutation.isPending || u.id === user?.id}
                          className="px-2 py-1 text-xs bg-destructive/10 text-destructive rounded hover:bg-destructive/20 disabled:opacity-50"
                        >
                          移除
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            queryClient.invalidateQueries({ queryKey: ['users'] })
          }}
        />
      )}

      {editingUser && (
        <EditUserRoleModal
          user={editingUser}
          roles={roles}
          onClose={() => setEditingUser(null)}
          onSuccess={() => {
            setEditingUser(null)
            queryClient.invalidateQueries({ queryKey: ['users'] })
          }}
        />
      )}
    </div>
  )
}

function CreateUserModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    phone: '',
    password: '',
    role_id: '' as number | '',
  })
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => apiClient.post('/users', {
      username: data.username,
      email: data.email,
      phone: data.phone || undefined,
      password: data.password,
    }),
    onSuccess: () => {
      onSuccess()
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || '创建失败')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    createMutation.mutate(formData)
  }

  return (
    <Modal
      open={true}
      onOpenChange={(open) => { if (!open) onClose() }}
      title="添加用户"
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>用户名</Label>
            <Input
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              placeholder="请输入用户名"
            />
          </div>
          <div className="space-y-2">
            <Label>邮箱</Label>
            <Input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="请输入邮箱"
            />
          </div>
          <div className="space-y-2">
            <Label>手机号（可选）</Label>
            <Input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              placeholder="请输入手机号"
            />
          </div>
          <div className="space-y-2">
            <Label>密码</Label>
            <Input
              type="password"
              required
              minLength={8}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="请输入密码（至少8位）"
            />
          </div>

          {error && (
            <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded">{error}</div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              取消
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </div>
        </form>
    </Modal>
  )
}

function EditUserRoleModal({ user, roles, onClose, onSuccess }: { user: UserItem; roles: Role[]; onClose: () => void; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const { data: tenants = [] } = useQuery<Tenant[]>({
    queryKey: ['all-tenants'],
    queryFn: () => apiClient.get('/tenants/public'),
  })
  const [tenantSelections, setTenantSelections] = useState<{ tenantId: number; roleId: number | null }[]>([])
  const [error, setError] = useState('')

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, tenantRoles }: { userId: number; tenantRoles: { tenant_id: number; role_id: number }[] }) =>
      apiClient.put(`/users/${userId}/role`, { tenant_roles: tenantRoles }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      onSuccess()
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || '更新失败')
    },
  })

  const handleTenantSelectionChange = (tenantId: number, checked: boolean) => {
    if (checked) {
      setTenantSelections([...tenantSelections, { tenantId, roleId: null }])
    } else {
      setTenantSelections(tenantSelections.filter(tr => tr.tenantId !== tenantId))
    }
  }

  const handleTenantRoleChange = (tenantId: number, roleId: number) => {
    setTenantSelections(tenantSelections.map(tr =>
      tr.tenantId === tenantId ? { ...tr, roleId } : tr
    ))
  }

  const tenantRoles = roles.filter(r => r.tenant_id != null)

  const canSubmit = tenantSelections.length > 0 && tenantSelections.every(tr => tr.roleId !== null)

  return (
    <Modal
      open={true}
      onOpenChange={(open) => { if (!open) onClose() }}
      title="调整用户权限"
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button
            onClick={() => {
              updateRoleMutation.mutate({
                userId: user.id,
                tenantRoles: tenantSelections.filter(tr => tr.roleId !== null).map(tr => ({
                  tenant_id: tr.tenantId,
                  role_id: tr.roleId as number,
                })),
              })
            }}
            disabled={!canSubmit || updateRoleMutation.isPending}
          >
            {updateRoleMutation.isPending ? '更新中...' : '确认'}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
          <div className="bg-muted p-4 rounded-lg">
            <div className="font-medium">{user.username}</div>
            <div className="text-sm text-muted-foreground">{user.email}</div>
          </div>

          {/* 租户角色 */}
          <div className="space-y-2">
            <Label>分配租户角色</Label>
            {tenants.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无可用租户</p>
            ) : (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-muted-foreground w-10"></th>
                      <th className="px-4 py-2 text-left font-medium text-muted-foreground">租户</th>
                      <th className="px-4 py-2 text-left font-medium text-muted-foreground">角色</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {tenants.map((tenant) => {
                      const selection = tenantSelections.find(tr => tr.tenantId === tenant.id)
                      const isSelected = !!selection
                      const availableRoles = tenantRoles.filter(r => r.tenant_id === tenant.id)
                      return (
                        <tr key={tenant.id} className={cn(isSelected && 'bg-primary/5')}>
                          <td className="px-4 py-2">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => handleTenantSelectionChange(tenant.id, e.target.checked)}
                              className="w-4 h-4 rounded border-gray-300"
                            />
                          </td>
                          <td className="px-4 py-2 font-medium text-foreground">{tenant.name}</td>
                          <td className="px-4 py-2">
                            <Select
                              value={selection?.roleId?.toString() || ''}
                              onValueChange={(v) => handleTenantRoleChange(tenant.id, Number(v))}
                              disabled={!isSelected}
                            >
                              <SelectTrigger className="w-full h-8">
                                <SelectValue placeholder="先选择租户" />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="">先选择租户</SelectItem>
                                {availableRoles.map((r) => (
                                  <SelectItem key={r.id} value={r.id.toString()}>{r.name}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              勾选租户后选择对应的角色
            </p>
          </div>

          {error && (
            <div className="text-destructive text-sm bg-destructive/10 p-3 rounded">
              {error}
            </div>
          )}
        </div>
    </Modal>
  )
}

// ============ 待审批用户 Tab (系统管理员) ============
interface PendingUser {
  id: number
  username: string
  email: string
  phone?: string
  requested_tenant_id?: number
  requested_tenant_name?: string
  created_at: string
}

interface TenantRoleSelection {
  tenantId: number
  roleId: number | null
}

export function PendingUsersTab() {
  const queryClient = useQueryClient()
  const [selectedUser, setSelectedUser] = useState<PendingUser | null>(null)
  const [selectedSystemRole, setSelectedSystemRole] = useState<number | null>(null)
  const [tenantSelections, setTenantSelections] = useState<TenantRoleSelection[]>([])

  const { data: pendingUsers = [], isLoading } = useQuery<PendingUser[]>({
    queryKey: ['admin', 'pending-users'],
    queryFn: () => apiClient.get('/admin/users/pending'),
  })

  const { data: roles = [] } = useQuery<Role[]>({
    queryKey: ['roles'],
    queryFn: () => apiClient.get('/roles'),
  })

  const { data: tenants = [] } = useQuery<Tenant[]>({
    queryKey: ['all-tenants'],
    queryFn: () => apiClient.get('/tenants/public'),
  })

  const approveMutation = useMutation({
    mutationFn: ({ userId, systemRoleId, tenantRoles }: { userId: number; systemRoleId?: number; tenantRoles: TenantRoleSelection[] }) =>
      apiClient.post(`/admin/users/${userId}/approve`, {
        system_role_id: systemRoleId || undefined,
        tenant_roles: tenantRoles.filter(tr => tr.roleId !== null).map(tr => ({
          tenant_id: tr.tenantId,
          role_id: tr.roleId,
        })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'pending-users'] })
      resetForm()
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (userId: number) =>
      apiClient.post(`/admin/users/${userId}/reject`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'pending-users'] })
    },
  })

  const resetForm = () => {
    setSelectedUser(null)
    setSelectedSystemRole(null)
    setTenantSelections([])
  }

  const handleApprove = (user: PendingUser) => {
    setSelectedUser(user)
    setSelectedSystemRole(null)
    // 预填充用户申请的租户
    if (user.requested_tenant_id) {
      setTenantSelections([{ tenantId: user.requested_tenant_id, roleId: null }])
    } else {
      setTenantSelections([])
    }
  }

  const confirmApprove = () => {
    if (!selectedUser) return
    // 至少要选择一个系统角色或租户角色
    if (!selectedSystemRole && tenantSelections.length === 0) return
    // 租户角色必须都已选择角色
    if (tenantSelections.some(tr => tr.roleId === null)) return

    approveMutation.mutate({
      userId: selectedUser.id,
      systemRoleId: selectedSystemRole || undefined,
      tenantRoles: tenantSelections,
    })
  }

  const handleReject = (userId: number) => {
    if (confirm('确定要拒绝该用户的注册申请吗？')) {
      rejectMutation.mutate(userId)
    }
  }

  const handleTenantSelectionChange = (tenantId: number, checked: boolean) => {
    if (checked) {
      setTenantSelections([...tenantSelections, { tenantId, roleId: null }])
    } else {
      setTenantSelections(tenantSelections.filter(tr => tr.tenantId !== tenantId))
    }
  }

  const handleTenantRoleChange = (tenantId: number, roleId: number) => {
    setTenantSelections(tenantSelections.map(tr =>
      tr.tenantId === tenantId ? { ...tr, roleId } : tr
    ))
  }

  const tenantRoles = roles.filter(r => r.tenant_id != null)
  const systemRoles = roles.filter(r => r.tenant_id === null && r.scope === 'system')

  const canApprove = (selectedSystemRole !== null) || (tenantSelections.length > 0 && tenantSelections.every(tr => tr.roleId !== null))

  return (
    <div className="space-y-6">
      <div className="bg-card rounded-xl shadow-sm border p-6">
        <div className="mb-6">
          <h3 className="text-lg font-medium mb-1">待审批用户</h3>
          <p className="text-sm text-muted-foreground">系统管理员 - 审批新用户注册申请</p>
        </div>

        {isLoading ? (
          <div className="text-center py-8 text-muted-foreground">加载中...</div>
        ) : pendingUsers.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            暂无待审批用户
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-muted-foreground border-b">
                  <th className="pb-3 font-medium">用户名</th>
                  <th className="pb-3 font-medium">邮箱</th>
                  <th className="pb-3 font-medium">手机号</th>
                  <th className="pb-3 font-medium">申请租户</th>
                  <th className="pb-3 font-medium">注册时间</th>
                  <th className="pb-3 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {pendingUsers.map((u) => (
                  <tr key={u.id} className="hover:bg-muted/50">
                    <td className="py-3 font-medium">{u.username}</td>
                    <td className="py-3 text-sm text-muted-foreground">{u.email}</td>
                    <td className="py-3 text-sm text-muted-foreground">{u.phone || '-'}</td>
                    <td className="py-3">
                      {u.requested_tenant_name ? (
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                          {u.requested_tenant_name}
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-sm">未指定</span>
                      )}
                    </td>
                    <td className="py-3 text-sm text-muted-foreground">
                      {new Date(u.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="py-3 text-right">
                      <Button
                        size="sm"
                        onClick={() => handleApprove(u)}
                        className="mr-2"
                      >
                        <Check className="w-4 h-4 mr-1" />
                        批准
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleReject(u.id)}
                        disabled={rejectMutation.isPending}
                      >
                        <X className="w-4 h-4 mr-1" />
                        拒绝
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 审批 Modal */}
      {selectedUser && (
        <Modal
          open={!!selectedUser}
          onOpenChange={(open) => { if (!open) resetForm() }}
          title="批准用户注册"
          size="lg"
          footer={
            <>
              <Button variant="outline" onClick={resetForm}>
                取消
              </Button>
              <Button
                onClick={confirmApprove}
                disabled={!canApprove || approveMutation.isPending}
              >
                {approveMutation.isPending ? '处理中...' : '确认批准'}
              </Button>
            </>
          }
        >
          <div className="space-y-4">
              <div className="bg-muted p-4 rounded-lg">
                <div className="font-medium">{selectedUser.username}</div>
                <div className="text-sm text-muted-foreground">{selectedUser.email}</div>
                {selectedUser.requested_tenant_name && (
                  <div className="text-sm text-green-600 mt-1">
                    申请租户: {selectedUser.requested_tenant_name}
                  </div>
                )}
              </div>

              {/* 系统级角色 */}
              <div className="space-y-2">
                <Label>系统级角色（可选）</Label>
                <Select
                  value={selectedSystemRole?.toString() || ''}
                  onValueChange={(v) => {
                    setSelectedSystemRole(v ? Number(v) : null)
                    if (v) {
                      setTenantSelections([])
                    }
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="不分配系统级角色" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">不分配系统级角色</SelectItem>
                    {systemRoles.map((r) => (
                      <SelectItem key={r.id} value={r.id.toString()}>{r.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedSystemRole && (
                  <p className="text-xs text-green-600">
                    超级管理员拥有所有租户权限，无需单独分配租户角色
                  </p>
                )}
              </div>

              {/* 租户角色 */}
              {!selectedSystemRole && (
                <div className="space-y-2">
                  <Label>分配租户角色</Label>
                  {tenants.length === 0 ? (
                    <p className="text-sm text-muted-foreground">暂无可用租户</p>
                  ) : (
                    <div className="border rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-muted">
                          <tr>
                            <th className="px-4 py-2 text-left font-medium text-muted-foreground w-10"></th>
                            <th className="px-4 py-2 text-left font-medium text-muted-foreground">租户</th>
                            <th className="px-4 py-2 text-left font-medium text-muted-foreground">角色</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {tenants.map((tenant) => {
                            const selection = tenantSelections.find(tr => tr.tenantId === tenant.id)
                            const isSelected = !!selection
                            const availableRoles = tenantRoles.filter(r => r.tenant_id === tenant.id)
                            return (
                              <tr key={tenant.id} className={cn(isSelected && 'bg-primary/5')}>
                                <td className="px-4 py-2">
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={(e) => handleTenantSelectionChange(tenant.id, e.target.checked)}
                                    className="w-4 h-4 rounded border-gray-300"
                                  />
                                </td>
                                <td className="px-4 py-2 font-medium text-foreground">{tenant.name}</td>
                                <td className="px-4 py-2">
                                  <Select
                                    value={selection?.roleId?.toString() || ''}
                                    onValueChange={(v) => handleTenantRoleChange(tenant.id, Number(v))}
                                    disabled={!isSelected}
                                  >
                                    <SelectTrigger className="w-full h-8">
                                      <SelectValue placeholder="先选择租户" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="">先选择租户</SelectItem>
                                      {availableRoles.map((r) => (
                                        <SelectItem key={r.id} value={r.id.toString()}>{r.name}</SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <p className="text-xs text-muted-foreground">
                    勾选租户后选择对应的角色，至少选择一个租户及其角色
                  </p>
                </div>
              )}

              {approveMutation.error && (
                <div className="text-destructive text-sm bg-destructive/10 p-3 rounded">
                  {approveMutation.error.message || '操作失败'}
                </div>
              )}
            </div>
        </Modal>
      )}
    </div>
  )
}
