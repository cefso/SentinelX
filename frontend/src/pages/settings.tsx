import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { toast } from '@/stores/toast-store'
import { User, Lock, Shield, Key, Users, Sparkles, Plus, ShieldCheck, Check, X } from 'lucide-react'

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
  webhook_url?: string
}

type SettingsTab = 'profile' | 'security' | 'tenant' | 'api-keys' | 'users' | 'ai' | 'pending'

interface Role {
  id: number
  name: string
  code: string
  tenant_id?: number
  scope?: string
}

const menuItems = [
  { key: 'profile' as const, label: '个人信息', icon: User },
  { key: 'security' as const, label: '安全设置', icon: Lock },
  { key: 'tenant' as const, label: '租户设置', icon: Shield },
  { key: 'api-keys' as const, label: 'API Keys', icon: Key },
  { key: 'users' as const, label: '用户管理', icon: Users },
  { key: 'ai' as const, label: 'AI设置', icon: Sparkles },
]

// 系统管理员专属菜单
const adminMenuItems = [
  { key: 'pending' as const, label: '待审批用户', icon: ShieldCheck },
]

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile')
  const { user } = useAuthStore()

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* 左侧导航 */}
      <div className="w-56 border-r bg-white shrink-0">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">系统设置</h2>
        </div>
        <nav className="p-2 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.key}
                onClick={() => setActiveTab(item.key)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === item.key
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </button>
            )
          })}
          {user?.is_system === true && (
            <>
              <div className="my-2 border-t" />
              {adminMenuItems.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.key}
                    onClick={() => setActiveTab(item.key)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === item.key
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    {item.label}
                  </button>
                )
              })}
            </>
          )}
        </nav>
      </div>

      {/* 右侧内容 */}
      <div className="flex-1 overflow-auto bg-gray-50 p-4 md:p-6 lg:p-8">
        {/* 内容区域 */}
        <div className="max-w-full">
          {activeTab === 'profile' && <ProfileTab />}
          {activeTab === 'security' && <SecurityTab />}
          {activeTab === 'tenant' && <TenantTab />}
          {activeTab === 'api-keys' && <ApiKeysTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'ai' && <AISettingsTab />}
          {activeTab === 'pending' && <PendingUsersTab />}
        </div>
      </div>
    </div>
  )
}

// ============ 个人信息 Tab ============
function ProfileTab() {
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

// ============ 安全设置 Tab ============
function SecurityTab() {
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

// ============ 租户设置 Tab ============
function TenantTab() {
  const { user } = useAuthStore()
  const { data: tenant } = useQuery<Tenant>({
    queryKey: ['currentTenant'],
    queryFn: () => apiClient.get('/tenants/current'),
  })

  return (
    <div className="space-y-6">
      {/* 当前租户信息 */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-medium mb-1">当前租户</h3>
            <p className="text-sm text-gray-500">查看租户配置</p>
          </div>
        </div>

        {!tenant ? (
          <div className="p-8 text-center">加载中...</div>
        ) : (
          <dl className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">租户名称</dt>
              <dd className="text-sm font-medium">{tenant.name}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">Slug</dt>
              <dd className="text-sm font-mono">{tenant.slug}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">告警配额</dt>
              <dd className="text-sm font-medium">{tenant.max_alerts.toLocaleString()}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">用户配额</dt>
              <dd className="text-sm font-medium">{tenant.max_users}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">规则配额</dt>
              <dd className="text-sm font-medium">{tenant.max_rules}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">渠道配额</dt>
              <dd className="text-sm font-medium">{tenant.max_channels}</dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-gray-500">告警QPS</dt>
              <dd className="text-sm font-medium">{tenant.alert_qps}</dd>
            </div>
            {tenant.webhook_url && (
              <div className="flex items-center justify-between py-3 border-t">
                <dt className="text-sm text-gray-500">Webhook URL</dt>
                <dd className="text-sm font-mono text-blue-600">{tenant.webhook_url}</dd>
              </div>
            )}
          </dl>
        )}
      </div>

      {/* 租户列表（仅系统管理员可见） */}
      {user?.is_system === true && <TenantList />}
    </div>
  )
}

// ============ 租户列表 ============
function TenantList() {
  const queryClient = useQueryClient()
  const { data: tenants = [] } = useQuery<Tenant[]>({
    queryKey: ['tenants'],
    queryFn: () => apiClient.get('/tenants'),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiClient.put(`/tenants/${id}`, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
    },
  })

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-4">所有租户</h3>
      {tenants.length === 0 ? (
        <div className="p-8 text-center text-gray-500">暂无租户</div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="text-left text-sm text-gray-500 border-b">
              <th className="pb-3 font-medium">名称</th>
              <th className="pb-3 font-medium">Slug</th>
              <th className="pb-3 font-medium">启用</th>
              <th className="pb-3 font-medium">告警配额</th>
              <th className="pb-3 font-medium">用户配额</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {tenants.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="py-3 font-medium">{t.name}</td>
                <td className="py-3 font-mono text-sm text-gray-500">{t.slug}</td>
                <td className="py-3">
                  <button
                    onClick={() => toggleMutation.mutate({ id: t.id, is_active: !t.is_active })}
                    disabled={toggleMutation.isPending}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50 ${
                      t.is_active ? 'bg-blue-600' : 'bg-gray-300'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        t.is_active ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </td>
                <td className="py-3 text-sm">{t.max_alerts.toLocaleString()}</td>
                <td className="py-3 text-sm">{t.max_users}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ============ API Keys Tab ============
function ApiKeysTab() {
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-md">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold">创建 API Key</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
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
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-lg hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              创建
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ============ 用户管理 Tab ============
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

function UsersTab() {
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

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-medium mb-1">用户管理</h3>
            <p className="text-sm text-gray-500">管理租户内的用户账户</p>
          </div>
          {canManageUsers && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              添加用户
            </button>
          )}
        </div>

        {users.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            暂无用户
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-gray-500 border-b">
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
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="py-3 font-medium">{u.username}</td>
                  <td className="py-3 text-sm text-gray-500">{u.email}</td>
                  <td className="py-3 text-sm text-gray-500">{u.phone || '-'}</td>
                  <td className="py-3">
                    <span className={`px-2 py-1 text-xs rounded ${
                      u.is_superuser ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                    }`}>
                      {u.is_superuser ? '管理员' : '用户'}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className={`px-2 py-1 text-xs rounded ${
                      u.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {u.is_active ? '活跃' : '禁用'}
                    </span>
                  </td>
                  {canManageUsers && (
                    <td className="py-3 text-right">
                      <button
                        onClick={() => setEditingUser(u)}
                        disabled={u.id === user?.id}
                        className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded hover:bg-blue-200 mr-2 disabled:opacity-50"
                      >
                        调整权限
                      </button>
                      <button
                        onClick={() => toggleActiveMutation.mutate({ id: u.id, is_active: !u.is_active })}
                        disabled={toggleActiveMutation.isPending || u.id === user?.id}
                        className={`px-2 py-1 text-xs rounded mr-2 ${
                          u.is_active
                            ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                            : 'bg-green-100 text-green-800 hover:bg-green-200'
                        } disabled:opacity-50`}
                      >
                        {u.is_active ? '禁用' : '启用'}
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`确定要从本租户移除用户 ${u.username} 吗？`)) {
                            removeUserMutation.mutate(u.id)
                          }
                        }}
                        disabled={removeUserMutation.isPending || u.id === user?.id}
                        className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 disabled:opacity-50"
                      >
                        移除
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
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

// ============ 创建用户 Modal ============
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-md">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold">添加用户</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
            <input
              type="text"
              required
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="请输入用户名"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
            <input
              type="email"
              required
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="请输入邮箱"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">手机号（可选）</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="请输入手机号"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              type="password"
              required
              minLength={8}
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              placeholder="请输入密码（至少8位）"
            />
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-lg hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ============ 编辑用户角色 Modal ============
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b sticky top-0 bg-white">
          <h2 className="text-xl font-bold">调整用户权限</h2>
        </div>
        <div className="p-6 space-y-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="font-medium">{user.username}</div>
            <div className="text-sm text-gray-500">{user.email}</div>
          </div>

          {/* 租户角色 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">分配租户角色</label>
            {tenants.length === 0 ? (
              <p className="text-sm text-gray-500">暂无可用租户</p>
            ) : (
              <div className="border rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-600 w-10"></th>
                      <th className="px-4 py-2 text-left font-medium text-gray-600">租户</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-600">角色</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {tenants.map((tenant) => {
                      const selection = tenantSelections.find(tr => tr.tenantId === tenant.id)
                      const isSelected = !!selection
                      const availableRoles = tenantRoles.filter(r => r.tenant_id === tenant.id)
                      return (
                        <tr key={tenant.id} className={isSelected ? 'bg-blue-50' : ''}>
                          <td className="px-4 py-2">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={(e) => handleTenantSelectionChange(tenant.id, e.target.checked)}
                              className="w-4 h-4 rounded border-gray-300"
                            />
                          </td>
                          <td className="px-4 py-2 font-medium text-gray-900">{tenant.name}</td>
                          <td className="px-4 py-2">
                            <select
                              value={selection?.roleId || ''}
                              onChange={(e) => handleTenantRoleChange(tenant.id, Number(e.target.value))}
                              disabled={!isSelected}
                              className="w-full px-2 py-1 border rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
                            >
                              <option value="">先选择租户</option>
                              {availableRoles.map((r) => (
                                <option key={r.id} value={r.id}>{r.name}</option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <p className="text-xs text-gray-500 mt-2">
              勾选租户后选择对应的角色
            </p>
          </div>

          {error && (
            <div className="text-red-600 text-sm bg-red-50 p-3 rounded">
              {error}
            </div>
          )}
        </div>
        <div className="p-6 border-t flex justify-end gap-3 sticky bottom-0 bg-white">
          <button
            onClick={onClose}
            className="px-4 py-2 border rounded-lg hover:bg-gray-50"
          >
            取消
          </button>
          <button
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
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {updateRoleMutation.isPending ? '更新中...' : '确认'}
          </button>
        </div>
      </div>
    </div>
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

function PendingUsersTab() {
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
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="mb-6">
          <h3 className="text-lg font-medium mb-1">待审批用户</h3>
          <p className="text-sm text-gray-500">系统管理员 - 审批新用户注册申请</p>
        </div>

        {isLoading ? (
          <div className="text-center py-8">加载中...</div>
        ) : pendingUsers.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            暂无待审批用户
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-gray-500 border-b">
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
                <tr key={u.id} className="hover:bg-gray-50">
                  <td className="py-3 font-medium">{u.username}</td>
                  <td className="py-3 text-sm text-gray-500">{u.email}</td>
                  <td className="py-3 text-sm text-gray-500">{u.phone || '-'}</td>
                  <td className="py-3">
                    {u.requested_tenant_name ? (
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                        {u.requested_tenant_name}
                      </span>
                    ) : (
                      <span className="text-gray-400 text-sm">未指定</span>
                    )}
                  </td>
                  <td className="py-3 text-sm text-gray-500">
                    {new Date(u.created_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="py-3 text-right">
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
        )}
      </div>

      {/* 审批 Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b sticky top-0 bg-white">
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

              {/* 系统级角色 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">系统级角色（可选）</label>
                <select
                  value={selectedSystemRole || ''}
                  onChange={(e) => {
                    setSelectedSystemRole(e.target.value ? Number(e.target.value) : null)
                    if (e.target.value) {
                      setTenantSelections([])
                    }
                  }}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">不分配系统级角色</option>
                  {systemRoles.map((r) => (
                    <option key={r.id} value={r.id}>{r.name}</option>
                  ))}
                </select>
                {selectedSystemRole && (
                  <p className="text-xs text-green-600 mt-1">
                    超级管理员拥有所有租户权限，无需单独分配租户角色
                  </p>
                )}
              </div>

              {/* 租户角色 */}
              {!selectedSystemRole && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">分配租户角色</label>
                  {tenants.length === 0 ? (
                    <p className="text-sm text-gray-500">暂无可用租户</p>
                  ) : (
                    <div className="border rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-2 text-left font-medium text-gray-600 w-10"></th>
                            <th className="px-4 py-2 text-left font-medium text-gray-600">租户</th>
                            <th className="px-4 py-2 text-left font-medium text-gray-600">角色</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {tenants.map((tenant) => {
                            const selection = tenantSelections.find(tr => tr.tenantId === tenant.id)
                            const isSelected = !!selection
                            const availableRoles = tenantRoles.filter(r => r.tenant_id === tenant.id)
                            return (
                              <tr key={tenant.id} className={isSelected ? 'bg-blue-50' : ''}>
                                <td className="px-4 py-2">
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={(e) => handleTenantSelectionChange(tenant.id, e.target.checked)}
                                    className="w-4 h-4 rounded border-gray-300"
                                  />
                                </td>
                                <td className="px-4 py-2 font-medium text-gray-900">{tenant.name}</td>
                                <td className="px-4 py-2">
                                  <select
                                    value={selection?.roleId || ''}
                                    onChange={(e) => handleTenantRoleChange(tenant.id, Number(e.target.value))}
                                    disabled={!isSelected}
                                    className="w-full px-2 py-1 border rounded focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
                                  >
                                    <option value="">先选择租户</option>
                                    {availableRoles.map((r) => (
                                      <option key={r.id} value={r.id}>{r.name}</option>
                                    ))}
                                  </select>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <p className="text-xs text-gray-500 mt-2">
                    勾选租户后选择对应的角色，至少选择一个租户及其角色
                  </p>
                </div>
              )}

              {approveMutation.error && (
                <div className="text-red-600 text-sm bg-red-50 p-3 rounded">
                  {approveMutation.error.message || '操作失败'}
                </div>
              )}
            </div>
            <div className="p-6 border-t flex justify-end gap-3 sticky bottom-0 bg-white">
              <button
                onClick={resetForm}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={confirmApprove}
                disabled={!canApprove || approveMutation.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
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

// ============ AI设置 Tab ============
function AISettingsTab() {
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-4')
  const [saved, setSaved] = useState(false)

  const providers = [
    { value: 'openai', label: 'OpenAI', models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
    { value: 'anthropic', label: 'Anthropic Claude', models: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'] },
    { value: 'qwen', label: '阿里云 Qwen', models: ['qwen-max', 'qwen-plus', 'qwen-turbo'] },
  ]

  const handleSave = () => {
    localStorage.setItem('ai_config', JSON.stringify({ provider, apiKey, model }))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-1">AI设置</h3>
      <p className="text-sm text-gray-500 mb-6">
        配置AI服务提供商，用于根因分析、内容润色等功能。API Key 仅存储在本地浏览器中。
      </p>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">AI提供商</label>
          <div className="grid grid-cols-3 gap-3">
            {providers.map((p) => (
              <button
                key={p.value}
                onClick={() => { setProvider(p.value); setModel(p.models[0]); }}
                className={`p-4 border rounded-xl flex flex-col items-center gap-2 transition-all ${
                  provider === p.value ? 'border-blue-500 bg-blue-50' : 'hover:border-gray-300'
                }`}
              >
                <span className="font-medium">{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="输入API Key"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">模型</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {providers.find(p => p.value === provider)?.models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-4 pt-4 border-t">
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            保存配置
          </button>
          {saved && <span className="text-sm text-green-600">配置已保存</span>}
        </div>
      </div>

      <div className="mt-8 pt-6 border-t">
        <h4 className="text-sm font-medium mb-4">AI功能说明</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="font-medium mb-1">🔍 根因分析</div>
            <div className="text-sm text-gray-600">自动分析告警发生的可能原因</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="font-medium mb-1">✨ 内容润色</div>
            <div className="text-sm text-gray-600">将告警内容润色成更易读格式</div>
          </div>
        </div>
      </div>
    </div>
  )
}