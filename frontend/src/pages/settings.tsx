import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'

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

interface User {
  id: number
  username: string
  email: string
  phone?: string
  is_superuser: boolean
}

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<'profile' | 'tenant' | 'api-keys'>('profile')
  const { user: authUser, setUser } = useAuthStore()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">系统设置</h1>
        <p className="text-gray-600">管理您的账户和系统配置</p>
      </div>

      <div className="flex border-b">
        <button
          onClick={() => setActiveTab('profile')}
          className={`px-4 py-2 border-b-2 ${activeTab === 'profile' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'}`}
        >
          个人信息
        </button>
        <button
          onClick={() => setActiveTab('tenant')}
          className={`px-4 py-2 border-b-2 ${activeTab === 'tenant' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'}`}
        >
          租户设置
        </button>
        <button
          onClick={() => setActiveTab('api-keys')}
          className={`px-4 py-2 border-b-2 ${activeTab === 'api-keys' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'}`}
        >
          API Keys
        </button>
        <button
          onClick={() => setActiveTab('ai')}
          className={`px-4 py-2 border-b-2 ${activeTab === 'ai' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'}`}
        >
          AI设置
        </button>
      </div>

      {activeTab === 'profile' && <ProfileTab />}
      {activeTab === 'tenant' && <TenantTab />}
      {activeTab === 'api-keys' && <ApiKeysTab />}
      {activeTab === 'ai' && <AISettingsTab />}
    </div>
  )
}

function ProfileTab() {
  const { user } = useAuthStore()
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState({
    username: user?.username || '',
    email: user?.email || '',
    phone: user?.phone || '',
  })

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-medium mb-4">个人信息</h2>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
          <input
            type="text"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            className="w-full px-3 py-2 border rounded-md"
            disabled
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">手机号</label>
          <input
            type="tel"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="w-full px-3 py-2 border rounded-md"
          />
        </div>
        <div className="pt-4 border-t">
          <button className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90">
            保存修改
          </button>
        </div>
      </div>
    </div>
  )
}

function TenantTab() {
  const { data: tenant } = useQuery<Tenant>({
    queryKey: ['currentTenant'],
    queryFn: () => apiClient.get('/tenants/current'),
  })

  if (!tenant) {
    return <div className="p-8 text-center">加载中...</div>
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-medium mb-4">租户信息</h2>
      <dl className="space-y-3">
        <div className="flex">
          <dt className="w-32 text-gray-500">租户名称</dt>
          <dd className="font-medium">{tenant.name}</dd>
        </div>
        <div className="flex">
          <dt className="w-32 text-gray-500">Slug</dt>
          <dd className="font-mono text-sm">{tenant.slug}</dd>
        </div>
        <div className="flex">
          <dt className="w-32 text-gray-500">告警配额</dt>
          <dd>{tenant.max_alerts.toLocaleString()}</dd>
        </div>
        <div className="flex">
          <dt className="w-32 text-gray-500">用户配额</dt>
          <dd>{tenant.max_users}</dd>
        </div>
        <div className="flex">
          <dt className="w-32 text-gray-500">规则配额</dt>
          <dd>{tenant.max_rules}</dd>
        </div>
        <div className="flex">
          <dt className="w-32 text-gray-500">渠道配额</dt>
          <dd>{tenant.max_channels}</dd>
        </div>
        <div className="flex">
          <dt className="w-32 text-gray-500">告警QPS</dt>
          <dd>{tenant.alert_qps}</dd>
        </div>
      </dl>
    </div>
  )
}

function ApiKeysTab() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const { data: apiKeys = [] } = useQuery<any[]>({
    queryKey: ['apiKeys'],
    queryFn: () => apiClient.get('/auth/api-keys'),
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-lg font-medium">API Keys</h2>
          <p className="text-sm text-gray-500">用于Agent和外部系统认证</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
        >
          创建 API Key
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        {apiKeys.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            暂无 API Keys
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">Key</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">权限</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">创建时间</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">最后使用</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {apiKeys.map((key: any) => (
                <tr key={key.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{key.name}</td>
                  <td className="px-4 py-3 font-mono text-sm">
                    <span className="text-gray-400">{key.key_prefix}...</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                      {key.permissions?.join(', ') || 'read'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {key.created_at ? new Date(key.created_at).toLocaleDateString('zh-CN') : '-'}
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString('zh-CN') : '从未使用'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button className="text-red-600 hover:text-red-800">
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
    permissions: ['read'],
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/auth/api-keys', data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys'] })
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate(formData)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-md">
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
              className="w-full px-3 py-2 border rounded-md"
              placeholder="如: Production Agent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">权限</label>
            <div className="space-y-2">
              {['read', 'write', 'admin'].map((perm) => (
                <label key={perm} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.permissions.includes(perm)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setFormData({ ...formData, permissions: [...formData.permissions, perm] })
                      } else {
                        setFormData({ ...formData, permissions: formData.permissions.filter(p => p !== perm) })
                      }
                    }}
                    className="rounded"
                  />
                  <span className="text-sm">{perm}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              创建
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

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
    // 保存到本地存储
    localStorage.setItem('ai_config', JSON.stringify({ provider, apiKey, model }))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-medium mb-4">AI配置</h2>
      <p className="text-sm text-gray-500 mb-6">
        配置AI服务提供商，用于根因分析、内容润色等功能。
        API Key仅存储在本地浏览器中。
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">AI提供商</label>
          <div className="grid grid-cols-3 gap-2">
            {providers.map((p) => (
              <button
                key={p.value}
                onClick={() => { setProvider(p.value); setModel(p.models[0]); }}
                className={`p-3 border rounded flex flex-col items-center ${provider === p.value ? 'border-blue-500 bg-blue-50' : ''}`}
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
            className="w-full px-3 py-2 border rounded-md"
            placeholder="输入API Key"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">模型</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-2 border rounded-md"
          >
            {providers.find(p => p.value === provider)?.models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div className="pt-4 border-t">
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
          >
            保存配置
          </button>
          {saved && <span className="ml-3 text-green-600">配置已保存</span>}
        </div>
      </div>

      <div className="mt-8 pt-6 border-t">
        <h3 className="text-md font-medium mb-3">AI功能说明</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="p-4 bg-gray-50 rounded">
            <div className="font-medium mb-1">🔍 根因分析</div>
            <div className="text-gray-600">自动分析告警发生的可能原因，给出调查方向</div>
          </div>
          <div className="p-4 bg-gray-50 rounded">
            <div className="font-medium mb-1">✨ 内容润色</div>
            <div className="text-gray-600">将告警内容润色成更易读的通知格式</div>
          </div>
          <div className="p-4 bg-gray-50 rounded">
            <div className="font-medium mb-1">💡 建议操作</div>
            <div className="text-gray-600">推荐处理告警的下一步具体操作</div>
          </div>
          <div className="p-4 bg-gray-50 rounded">
            <div className="font-medium mb-1">📊 影响预测</div>
            <div className="text-gray-600">预测告警未处理可能造成的影响</div>
          </div>
        </div>
      </div>
    </div>
  )
}