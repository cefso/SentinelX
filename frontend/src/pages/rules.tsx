import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { FIELD_CONFIGS } from '@/components/condition/constants'
import { generateCode } from '@/utils/code'
import { RulesLayout } from '@/components/rules/RulesLayout'
import { HelpCircle } from 'lucide-react'
import { NotificationTemplate } from './templates'

export type { Condition }

interface Rule {
  id: number
  name: string
  code: string
  description?: string
  conditions: Condition[]
  condition_mode: string
  actions: (string | { channel_id: number; template_id?: number })[]
  priority: number
  is_active: boolean
  suppress_config?: any
  aggregate_config?: any
  deduplication_config?: any
  match_count: number
  last_match_at?: string
  created_at: string
  updated_at: string
}

export function RulesPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<Rule | null>(null)
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all')

  const { data: rules = [], isLoading } = useQuery<Rule[]>({
    queryKey: ['rules', filter],
    queryFn: () => {
      const params = filter === 'active' ? { is_active: true } : filter === 'inactive' ? { is_active: false } : {}
      return apiClient.get('/rules', params)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (ruleId: number) => apiClient.delete(`/rules/${ruleId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ ruleId, is_active }: { ruleId: number; is_active: boolean }) =>
      apiClient.put(`/rules/${ruleId}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules'] }),
  })

  const handleEdit = (rule: Rule) => {
    setEditingRule(rule)
    setShowModal(true)
  }

  const handleCreate = () => {
    setEditingRule(null)
    setShowModal(true)
  }

  return (
    <RulesLayout>
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          路由规则决定告警匹配后发送到哪些通知渠道
        </p>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700"
        >
          创建路由规则
        </button>
      </div>

      <div className="flex gap-2">
        {[
          { key: 'all' as const, label: '全部', count: rules.length },
          { key: 'active' as const, label: '启用中' },
          { key: 'inactive' as const, label: '停用中' },
        ].map((item) => (
          <button
            key={item.key}
            onClick={() => setFilter(item.key)}
            className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
              filter === item.key
                ? 'bg-blue-100 text-blue-700 font-medium'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {item.label}{item.count !== undefined && ` (${item.count})`}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : rules.length === 0 ? (
          <div className="p-12 text-center">
            <div className="text-4xl mb-3 text-blue-200">
              <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="text-gray-500 font-medium">暂无路由规则</div>
            <div className="text-sm text-gray-400 mt-1">创建路由规则将告警发送到指定通知渠道</div>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">规则名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">条件</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">优先级</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">匹配次数</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">状态</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium">{rule.name}</div>
                    <div className="text-sm text-gray-500">{rule.code}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm">
                      {rule.conditions.length} 个条件 ({rule.condition_mode})
                    </div>
                    <div className="text-xs text-gray-400">
                      {rule.conditions.slice(0, 2).map((c, i) => {
                        const fc = FIELD_CONFIGS.find(f => f.value === c.field)
                        return (
                          <span key={i} className="mr-1">
                            {fc?.label || c.field} {c.operator} {String(c.value)}
                          </span>
                        )
                      })}
                      {rule.conditions.length > 2 && '...'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-sm bg-blue-100 text-blue-800 rounded">
                      {rule.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm">{rule.match_count}</div>
                    {rule.last_match_at && (
                      <div className="text-xs text-gray-400">
                        {new Date(rule.last_match_at).toLocaleDateString('zh-CN')}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleMutation.mutate({ ruleId: rule.id, is_active: !rule.is_active })}
                      disabled={toggleMutation.isPending}
                      className={`px-2 py-1 text-xs rounded disabled:opacity-50 ${rule.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}
                    >
                      {rule.is_active ? '启用' : '停用'}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleEdit(rule)}
                      className="text-blue-600 hover:text-blue-800 mr-3"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('确定要删除该规则吗？')) {
                          deleteMutation.mutate(rule.id)
                        }
                      }}
                      disabled={deleteMutation.isPending}
                      className="text-red-600 hover:text-red-800 disabled:opacity-50"
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

      {showModal && (
        <RuleModal
          rule={editingRule}
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            queryClient.invalidateQueries({ queryKey: ['rules'] })
          }}
          initialConditions={[]}
        />
      )}
    </RulesLayout>
  )
}

export function RuleModal({ rule, onClose, onSuccess, initialConditions, showModal: _showModal }: { rule: Rule | null; onClose: () => void; onSuccess: () => void; initialConditions?: Condition[]; showModal?: boolean }) {
  // Channel -> template mapping: { channelId: templateId | null }
  const [channelTemplateMap, setChannelTemplateMap] = useState<Record<number, number | null>>(() => {
    // Initialize from existing rule actions (new format)
    const map: Record<number, number | null> = {}
    const actions = rule?.actions || []
    for (const action of actions) {
      if (typeof action === 'object' && action !== null) {
        map[action.channel_id] = action.template_id ?? null
      }
    }
    return map
  })

  const [formData, setFormData] = useState({
    name: rule?.name || '',
    code: rule?.code || '',
    description: rule?.description || '',
    condition_mode: rule?.condition_mode || 'and',
    priority: rule?.priority || 0,
    conditions: rule?.conditions || initialConditions || [{ field: 'severity', operator: 'in', value: ['critical'] }],
    selected_channels: (() => {
      const channels: number[] = []
      const actions = rule?.actions || []
      for (const action of actions) {
        if (typeof action === 'object' && action !== null) {
          channels.push(action.channel_id)
        } else if (typeof action === 'string' || typeof action === 'number') {
          channels.push(Number(action))
        }
      }
      return channels
    })(),
  })

  // 监听 initialConditions 变化
  useEffect(() => {
    if (initialConditions && initialConditions.length > 0 && !rule) {
      setFormData(prev => ({ ...prev, conditions: initialConditions }))
    }
  }, [initialConditions, rule])

  const { data: channels = [] } = useQuery<any[]>({
    queryKey: ['channels'],
    queryFn: () => apiClient.get('/channels', { is_active: true }),
  })

  const { data: templates = [] } = useQuery<NotificationTemplate[]>({
    queryKey: ['templates'],
    queryFn: () => apiClient.get('/templates'),
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/rules', data),
    onSuccess,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/rules/${rule?.id}`, data),
    onSuccess,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // New action format with channel->template mapping
    const actions = formData.selected_channels.map((channelId: number) => ({
      channel_id: channelId,
      template_id: channelTemplateMap[channelId] ?? undefined,
    }))
    const payload = {
      name: formData.name,
      code: rule ? formData.code : generateCode(formData.name),
      description: formData.description,
      conditions: formData.conditions,
      condition_mode: formData.condition_mode,
      priority: formData.priority,
      actions,
      deduplication_config: null,
      aggregate_config: null,
      suppress_config: null,
    }
    if (rule) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-auto">
        <div className="p-6 border-b border-blue-100 bg-blue-50/50">
          <h2 className="text-xl font-bold text-blue-900">{rule ? '编辑路由规则' : initialConditions?.length ? '快捷创建路由规则' : '创建路由规则'}</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">规则名称</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 border rounded-md"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">条件组合方式</label>
              <select
                value={formData.condition_mode}
                onChange={(e) => setFormData({ ...formData, condition_mode: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="and">AND (全部满足)</option>
                <option value="or">OR (任一满足)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
              <input
                type="number"
                min="0"
                max="1000"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">条件</label>
            <ConditionEditor
              conditions={formData.conditions}
              onChange={(conditions) => setFormData({ ...formData, conditions })}
              fields={FIELD_CONFIGS}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">通知渠道</label>
            <div className="space-y-2">
              {channels.length === 0 ? (
                <div className="text-sm text-gray-500">暂无可用渠道，请先创建通知渠道</div>
              ) : (
                channels.map((channel: any) => {
                  const isSelected = formData.selected_channels.includes(channel.id)
                  const channelTemplates = (templates as NotificationTemplate[]).filter(
                    (t: NotificationTemplate) => t.channel_type === channel.channel_type
                  )
                  const selectedTemplateId = channelTemplateMap[channel.id] ?? null

                  return (
                    <div key={channel.id} className="p-2 border rounded hover:bg-gray-50 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormData({
                                ...formData,
                                selected_channels: [...formData.selected_channels, channel.id],
                              })
                            } else {
                              setFormData({
                                ...formData,
                                selected_channels: formData.selected_channels.filter((id: number) => id !== channel.id),
                              })
                              const newMap = { ...channelTemplateMap }
                              delete newMap[channel.id]
                              setChannelTemplateMap(newMap)
                            }
                          }}
                          className="rounded"
                        />
                        <span className="font-medium">{channel.name}</span>
                        <span className="text-sm text-gray-500">({channel.channel_type})</span>
                      </div>

                      {isSelected && channelTemplates.length > 0 && (
                        <div className="ml-6 flex items-center gap-2">
                          <span className="text-xs text-gray-500">模板:</span>
                          <select
                            value={selectedTemplateId ?? ''}
                            onChange={(e) => {
                              const val = e.target.value
                              setChannelTemplateMap({
                                ...channelTemplateMap,
                                [channel.id]: val ? Number(val) : null,
                              })
                            }}
                            className="text-sm px-2 py-1 border rounded"
                          >
                            <option value="">使用渠道默认</option>
                            {channelTemplates.map((t: NotificationTemplate) => (
                              <option key={t.id} value={t.id}>
                                {t.name}{t.is_default ? ' (默认)' : ''}
                              </option>
                            ))}
                          </select>
                          {!selectedTemplateId && (
                            <span className="text-xs text-gray-400 flex items-center gap-0.5" title="未选择模板时使用渠道的默认模板">
                              <HelpCircle className="w-3 h-3" />
                              将使用渠道默认模板
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {rule ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
