import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { User, Lock, Shield, Key, Users, Sparkles, UserCircle } from 'lucide-react'

interface Tenant {
  id: number
  name: string
  slug: string
  max_alerts: number
  max_users: number
  max_rules: number
  max_channels: number
  alert_qps: number
  config: Record<string, any>
}

type SettingsTab = 'profile' | 'security' | 'tenant' | 'api-keys' | 'users' | 'ai'

const menuItems = [
  { key: 'profile' as const, label: '个人信息', icon: User },
  { key: 'security' as const, label: '安全设置', icon: Lock },
  { key: 'tenant' as const, label: '租户设置', icon: Shield },
  { key: 'api-keys' as const, label: 'API Keys', icon: Key },
  { key: 'users' as const, label: '用户管理', icon: Users },
  { key: 'ai' as const, label: 'AI设置', icon: Sparkles },
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
        </nav>
      </div>

      {/* 右侧内容 */}
      <div className="flex-1 overflow-auto bg-gray-50 p-8">
        {/* 顶部用户信息 */}
        <div className="flex justify-end mb-6">
          <div className="flex items-center gap-3">
            <UserCircle className="w-8 h-8 text-gray-400" />
            <span className="text-sm font-medium text-gray-700">{user?.username}</span>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="max-w-3xl">
          {activeTab === 'profile' && <ProfileTab />}
          {activeTab === 'security' && <SecurityTab />}
          {activeTab === 'tenant' && <TenantTab />}
          {activeTab === 'api-keys' && <ApiKeysTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'ai' && <AISettingsTab />}
        </div>
      </div>
    </div>
  )
}

// ============ 个人信息 Tab ============
function ProfileTab() {
  const { user, setUser } = useAuthStore()
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    email: user?.email || '',
    phone: user?.phone || '',
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const updateMutation = useMutation({
    mutationFn: (data: { email: string; phone?: string }) =>
      apiClient.put(`/users/${user?.id}`, data),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
    onError: (err: any) => {
      alert(err.response?.data?.detail || '更新失败')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    updateMutation.mutate(formData, {
      onSettled: () => setSaving(false),
    })
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
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">手机号</label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div className="flex items-center gap-4 pt-4 border-t">
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存修改'}
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
  const [saving, setSaving] = useState(false)
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

    setSaving(true)
    updateMutation.mutate(
      { old_password: currentPassword, new_password: newPassword },
      { onSettled: () => setSaving(false) }
    )
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
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? '修改中...' : '修改密码'}
          </button>
        </div>
      </form>
    </div>
  )
}

// ============ 租户设置 Tab ============
function TenantTab() {
  const { data: tenant } = useQuery<Tenant>({
    queryKey: ['currentTenant'],
    queryFn: () => apiClient.get('/tenants/current'),
  })

  if (!tenant) {
    return <div className="p-8 text-center">加载中...</div>
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-1">租户设置</h3>
      <p className="text-sm text-gray-500 mb-6">查看您的租户配置</p>

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
      </dl>
    </div>
  )
}

// ============ API Keys Tab ============
function ApiKeysTab() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const { data } = useQuery<{ api_keys: any[] }>({
    queryKey: ['apiKeys'],
    queryFn: () => apiClient.get('/auth/api-keys'),
  })
  const apiKeys = data?.api_keys || []

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
                    <button className="text-red-600 hover:text-red-800 text-sm">删除</button>
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
      alert(err.response?.data?.detail || '创建失败')
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
  created_at: string
}

function UsersTab() {
  const { data: users = [] } = useQuery<UserItem[]>({
    queryKey: ['users'],
    queryFn: () => apiClient.get('/users'),
  })

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-lg font-medium mb-1">用户管理</h3>
          <p className="text-sm text-gray-500">管理租户内的用户账户</p>
        </div>
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
            </tr>
          </thead>
          <tbody className="divide-y">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50">
                <td className="py-3 font-medium">{user.username}</td>
                <td className="py-3 text-sm text-gray-500">{user.email}</td>
                <td className="py-3 text-sm text-gray-500">{user.phone || '-'}</td>
                <td className="py-3">
                  <span className={`px-2 py-1 text-xs rounded ${
                    user.is_superuser ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                  }`}>
                    {user.is_superuser ? '管理员' : '用户'}
                  </span>
                </td>
                <td className="py-3">
                  <span className={`px-2 py-1 text-xs rounded ${
                    user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {user.is_active ? '活跃' : '禁用'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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