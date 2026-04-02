import React, { useState, useMemo, FormEvent } from 'react'
import { Cloud, Box, Zap, Code, Server, BarChart3, CloudCog, Copy, Check, ToggleLeft, ToggleRight, RefreshCw, Plus, Settings } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '@/stores/auth-store'
import { apiClient } from '@/services/api'

interface AlertSourceConfig {
  id: string
  name: string
  description: string
  icon: React.ElementType
  接入方式: string
  配置说明: string[]
}

interface AlertSource {
  id: number
  name: string
  code: string
  source_type: string
  config: Record<string, any>
  description?: string
  is_active: boolean
  alert_count: number
  last_alert_at?: string
  created_at: string
}

const alertSourceTypes: AlertSourceConfig[] = [
  {
    id: 'prometheus',
    name: 'Prometheus / Alertmanager',
    description: '适用于 Prometheus + Alertmanager 架构的告警接入',
    icon: Server,
    接入方式: 'Webhook',
    配置说明: [
      '在 Alertmanager 配置文件中添加 webhook',
      '设置接收地址为平台的 Webhook URL',
    ],
  },
  {
    id: 'grafana',
    name: 'Grafana',
    description: '接入 Grafana 告警，支持 Grafana 8.x 及以上版本的告警通道',
    icon: BarChart3,
    接入方式: 'Webhook',
    配置说明: [
      '在 Grafana 中创建 Notification channel',
      '选择 Webhook 类型',
      '填入平台的 Webhook URL',
    ],
  },
  {
    id: 'aliyun_cms',
    name: '阿里云云监控1.0',
    description: '接入阿里云云监控1.0告警，支持 URL-encoded form data 格式回调',
    icon: Cloud,
    接入方式: 'Webhook',
    配置说明: [
      '登录阿里云云监控控制台',
      '创建报警规则，选择"回调模式"',
      '填入平台的 Webhook 地址',
      '告警内容以 form data 格式发送',
    ],
  },
  {
    id: 'aliyun_cms2',
    name: '阿里云云监控2.0',
    description: '接入阿里云云监控2.0告警，支持阈值报警和事件报警，JSON 格式回调',
    icon: Cloud,
    接入方式: 'Webhook',
    配置说明: [
      '登录云监控2.0控制台 → 告警中心 → 通知管理 → 通知对象',
      '新建 Webhook，填入平台的回调地址',
      '设置请求方法为 POST，数据格式为 JSON',
      '可选配置 Headers（如需要鉴权）',
    ],
  },
  {
    id: 'tencent',
    name: '腾讯云',
    description: '接入腾讯云云监控告警，支持多种告警类型',
    icon: Cloud,
    接入方式: 'Webhook',
    配置说明: [
      '登录腾讯云控制台',
      '创建告警策略，选择 Webhook 回调',
      '填入平台的 Webhook 地址',
    ],
  },
  {
    id: 'huawei',
    name: '华为云云监控',
    description: '接入华为云云监控告警，支持阈值报警和事件告警',
    icon: CloudCog,
    接入方式: 'Webhook',
    配置说明: [
      '登录华为云云监控控制台',
      '创建主题并设置 HTTP 订阅',
      '填入平台的 Webhook 地址',
    ],
  },
  {
    id: 'zabbix',
    name: 'Zabbix',
    description: '适用于 Zabbix 监控系统的告警接入',
    icon: Box,
    接入方式: 'Webhook',
    配置说明: [
      '在 Zabbix 中配置 Media type',
      '选择 Webhook 类型',
      '填入平台的 Webhook URL',
    ],
  },
  {
    id: 'custom',
    name: '自定义',
    description: '通过 Webhook API 接入任意数据源的告警',
    icon: Code,
    接入方式: 'Webhook API',
    配置说明: [
      '使用 POST 方法发送告警',
      '请求体为 JSON 格式',
      '包含必要字段：title, message, severity, labels',
    ],
  },
]

export function AlertSourcesPage() {
  const { currentTenant } = useAuthStore()
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingSource, setEditingSource] = useState<AlertSource | null>(null)
  const [defaultSourceType, setDefaultSourceType] = useState<string>('prometheus')
  const queryClient = useQueryClient()

  // 获取已配置的告警源列表
  const { data: sources = [], isLoading: sourcesLoading } = useQuery<AlertSource[]>({
    queryKey: ['alert-sources'],
    queryFn: () => apiClient.get('/sources'),
  })

  // 获取告警统计
  const { data: stats } = useQuery<{ total: number; firing: number; resolved: number; critical: number }>({
    queryKey: ['alertStats'],
    queryFn: () => apiClient.get('/alerts/stats'),
  })

  // 获取告警列表用于统计
  const { data: alertsData } = useQuery<{ items: any[] }>({
    queryKey: ['alerts-for-sources'],
    queryFn: () => apiClient.get('/alerts', { page_size: 1000 }),
  })

  // 按来源统计告警数量
  const sourceStats = useMemo(() => {
    if (!alertsData?.items) return {}
    const stats: Record<string, { total: number; firing: number }> = {}
    for (const alert of alertsData.items) {
      if (!stats[alert.source]) {
        stats[alert.source] = { total: 0, firing: 0 }
      }
      stats[alert.source].total++
      if (alert.status === 'firing') stats[alert.source].firing++
    }
    return stats
  }, [alertsData])

  // 切换告警源启用状态
  const toggleSourceMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiClient.put(`/sources/${id}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alert-sources'] }),
  })

  // 删除告警源
  const deleteSourceMutation = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/sources/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['alert-sources'] }),
  })

  // 获取当前租户的 webhook URL 前缀
  const webhookBaseUrl = currentTenant?.slug
    ? `/api/v1/webhooks/${currentTenant.slug}`
    : '/api/v1/webhooks/{tenant_slug}'

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  const handleEdit = (source: AlertSource) => {
    setEditingSource(source)
    setShowCreateModal(true)
  }

  const handleCreate = () => {
    setEditingSource(null)
    setShowCreateModal(true)
  }

  // 检查某类型是否已配置
  const isSourceConfigured = (type: string) => sources.some(s => s.source_type === type)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">告警提供商</h1>
          <p className="text-gray-500 mt-1">配置和管理告警接入渠道</p>
          {currentTenant && (
            <div className="mt-2 text-sm text-blue-600">
              当前租户：{currentTenant.name} (Slug: {currentTenant.slug})
            </div>
          )}
        </div>
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          添加配置
        </button>
      </div>

      {/* 已配置的告警源 */}
      {sources.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="p-4 border-b">
            <h2 className="text-lg font-semibold">已配置的告警源</h2>
          </div>
          {sourcesLoading ? (
            <div className="p-8 text-center text-gray-500">加载中...</div>
          ) : (
            <div className="divide-y">
              {sources.map((source) => {
                const typeInfo = alertSourceTypes.find(t => t.id === source.source_type)
                const Icon = typeInfo?.icon || Code
                const stat = sourceStats[source.source_type] || { total: 0, firing: 0 }
                return (
                  <div key={source.id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-lg ${source.is_active ? 'bg-green-50' : 'bg-gray-50'}`}>
                          <Icon className={`w-5 h-5 ${source.is_active ? 'text-green-600' : 'text-gray-400'}`} />
                        </div>
                        <div>
                          <div className="font-medium">{source.name}</div>
                          <div className="text-sm text-gray-500">
                            {source.code} • {typeInfo?.name || source.source_type}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-center">
                          <div className="text-lg font-bold">{stat.total}</div>
                          <div className="text-xs text-gray-500">总告警</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-bold text-red-600">{stat.firing}</div>
                          <div className="text-xs text-gray-500">触发中</div>
                        </div>
                        <button
                          onClick={() => toggleSourceMutation.mutate({ id: source.id, is_active: !source.is_active })}
                          disabled={toggleSourceMutation.isPending}
                          className={`p-2 rounded-lg ${source.is_active ? 'text-green-600' : 'text-gray-400'}`}
                          title={source.is_active ? '已启用' : '已停用'}
                        >
                          {source.is_active ? <ToggleRight className="w-6 h-6" /> : <ToggleLeft className="w-6 h-6" />}
                        </button>
                        <button
                          onClick={() => handleEdit(source)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                        >
                          <Settings className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('确定要删除该告警源配置吗？')) {
                              deleteSourceMutation.mutate(source.id)
                            }
                          }}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                        >
                          <span className="text-sm">删除</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* 告警源类型 - 卡片式响应式布局 */}
      <div>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900">支持的告警源类型</h2>
          <p className="text-sm text-gray-500">点击 Webhook 地址可直接复制</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {alertSourceTypes.map((sourceType) => {
            const Icon = sourceType.icon
            // 统一使用 /aliyun_cms 端点（支持 JSON 和 Form Data）
            const webhookUrl = sourceType.id === 'custom'
              ? `${webhookBaseUrl}/custom`
              : `${webhookBaseUrl}/${sourceType.id}`
            const isConfigured = isSourceConfigured(sourceType.id)
            return (
              <div
                key={sourceType.id}
                className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md hover:border-blue-200 transition-all duration-200 flex flex-col"
              >
                {/* 卡片头部 */}
                <div className="p-4 flex-1">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg ${isConfigured ? 'bg-green-50' : 'bg-blue-50'}`}>
                        <Icon className={`w-5 h-5 ${isConfigured ? 'text-green-600' : 'text-blue-600'}`} />
                      </div>
                      <div>
                        <div className="font-semibold text-gray-900">{sourceType.name}</div>
                        <div className="text-xs text-gray-500">{sourceType.description}</div>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-1 mb-3">
                    <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 rounded">
                      {sourceType.接入方式}
                    </span>
                    {isConfigured && (
                      <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                        已配置
                      </span>
                    )}
                  </div>

                  {/* 配置步骤 */}
                  <div className="space-y-1 mb-3">
                    {sourceType.配置说明.slice(0, 2).map((step, idx) => (
                      <div key={idx} className="flex gap-2 text-xs text-gray-600">
                        <span className="text-blue-500 shrink-0">{idx + 1}.</span>
                        <span className="truncate">{step}</span>
                      </div>
                    ))}
                    {sourceType.配置说明.length > 2 && (
                      <div className="text-xs text-gray-400 pl-5">+{sourceType.配置说明.length - 2} 更多步骤</div>
                    )}
                  </div>

                  {/* Webhook URL */}
                  <div className="mt-auto">
                    <div className="flex items-center gap-1 mb-1">
                      <span className="text-xs text-gray-500">Webhook:</span>
                      <button
                        onClick={() => handleCopy(webhookUrl, sourceType.id)}
                        className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1"
                      >
                        {copiedId === sourceType.id ? (
                          <><Check className="w-3 h-3" /> 已复制</>
                        ) : (
                          <><Copy className="w-3 h-3" /> 复制</>
                        )}
                      </button>
                    </div>
                    <code className="block text-xs bg-gray-50 px-2 py-1 rounded font-mono text-gray-700 break-all leading-tight">
                      {webhookUrl}
                    </code>
                  </div>
                </div>

                {/* 卡片底部操作 */}
                <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
                  <button
                    onClick={() => {
                      setEditingSource(null)
                      setDefaultSourceType(sourceType.id)
                      setShowCreateModal(true)
                    }}
                    className="w-full flex items-center justify-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
                  >
                    <Plus className="w-4 h-4" />
                    {isConfigured ? '编辑配置' : '添加配置'}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* 接入统计 */}
      <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">接入统计</h3>
          <button
            onClick={() => queryClient.invalidateQueries()}
            className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
          >
            <RefreshCw className="w-4 h-4" />
            刷新
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-gray-900">{sources.length}</div>
            <div className="text-sm text-gray-500">已配置来源</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-green-600">{sources.filter(s => s.is_active).length}</div>
            <div className="text-sm text-gray-500">活跃连接</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-blue-600">{stats?.total || 0}</div>
            <div className="text-sm text-gray-500">总告警</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-yellow-600">{stats?.firing || 0}</div>
            <div className="text-sm text-gray-500">触发中</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-red-600">{stats?.critical || 0}</div>
            <div className="text-sm text-gray-500">严重告警</div>
          </div>
        </div>
      </div>

      {/* 快速开始 */}
      <div className="p-6 bg-blue-50 rounded-xl border border-blue-100">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Zap className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-blue-900 mb-2">快速开始</h3>
            <p className="text-sm text-blue-700 mb-4">
              选择一个告警提供商，按照配置步骤完成接入。配置完成后，告警数据将自动同步到平台。
            </p>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
              查看接入文档
            </button>
          </div>
        </div>
      </div>

      {showCreateModal && (
        <SourceModal
          source={editingSource}
          defaultSourceType={editingSource ? undefined : defaultSourceType}
          alertSourceTypes={alertSourceTypes}
          webhookBaseUrl={webhookBaseUrl}
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false)
            queryClient.invalidateQueries({ queryKey: ['alert-sources'] })
          }}
        />
      )}
    </div>
  )
}

// 告警源配置 Modal
function SourceModal({
  source,
  defaultSourceType,
  alertSourceTypes,
  webhookBaseUrl,
  onClose,
  onSuccess,
}: {
  source: AlertSource | null
  defaultSourceType?: string
  alertSourceTypes: AlertSourceConfig[]
  webhookBaseUrl: string
  onClose: () => void
  onSuccess: () => void
}) {
  const [formData, setFormData] = useState({
    name: source?.name || '',
    code: source?.code || '',
    source_type: source?.source_type || defaultSourceType || 'prometheus',
    description: source?.description || '',
    config: source?.config || {},
    is_active: source?.is_active ?? true,
  })
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/sources', data),
    onSuccess,
    onError: (err: any) => setError(err.response?.data?.detail || '创建失败'),
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/sources/${source?.id}`, data),
    onSuccess,
    onError: (err: any) => setError(err.response?.data?.detail || '更新失败'),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (source) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const currentType = alertSourceTypes.find(t => t.id === formData.source_type)
  // 统一使用 /{source_type} 端点（支持 JSON 和 Form Data）
  const webhookUrl = formData.source_type === 'custom'
    ? `${webhookBaseUrl}/custom`
    : `${webhookBaseUrl}/${formData.source_type}`

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-lg max-h-[90vh] overflow-auto">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold">{source ? '编辑告警源' : '添加告警源'}</h2>
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
              placeholder="如: 生产环境 Prometheus"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">代码</label>
            <input
              type="text"
              required
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              placeholder="如: prod-prometheus"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">告警源类型</label>
            <select
              value={formData.source_type}
              onChange={(e) => setFormData({ ...formData, source_type: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              disabled={!!source}
            >
              {alertSourceTypes.map((type) => (
                <option key={type.id} value={type.id}>{type.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              rows={2}
              placeholder="描述此告警源的用途"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
            <code className="block text-xs bg-gray-50 px-3 py-2 rounded font-mono break-all">
              {webhookUrl}
            </code>
            <p className="text-xs text-gray-500 mt-1">
              在 {currentType?.name} 中配置此 URL 作为 Webhook 回调地址
            </p>
          </div>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm">启用</span>
            </label>
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
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {source ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
