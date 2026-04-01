import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'

interface Condition {
  field: string
  operator: string
  value: any
}

interface Rule {
  id: number
  name: string
  code: string
  description?: string
  conditions: Condition[]
  condition_mode: string
  actions: string[]
  priority: number
  is_active: boolean
  suppress_config?: any
  aggregate_config?: any
  match_count: number
  last_match_at?: string
  created_at: string
  updated_at: string
}

const OPERATORS = [
  { value: 'eq', label: '等于' },
  { value: 'ne', label: '不等于' },
  { value: 'gt', label: '大于' },
  { value: 'gte', label: '大于等于' },
  { value: 'lt', label: '小于' },
  { value: 'lte', label: '小于等于' },
  { value: 'contains', label: '包含' },
  { value: 'regex', label: '正则匹配' },
  { value: 'in', label: '在列表中' },
  { value: 'not_in', label: '不在列表中' },
]

const SEVERITY_OPTIONS = ['critical', 'high', 'medium', 'low', 'info']
const SOURCE_OPTIONS = ['prometheus', 'alertmanager', 'zabbix', 'aliyun', 'tencent', 'custom']

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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">规则管理</h1>
          <p className="text-gray-600">配置告警路由规则和条件</p>
        </div>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
        >
          创建规则
        </button>
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded ${filter === 'all' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100'}`}
        >
          全部 ({rules.length})
        </button>
        <button
          onClick={() => setFilter('active')}
          className={`px-3 py-1 rounded ${filter === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}
        >
          启用中
        </button>
        <button
          onClick={() => setFilter('inactive')}
          className={`px-3 py-1 rounded ${filter === 'inactive' ? 'bg-red-100 text-red-700' : 'bg-gray-100'}`}
        >
          停用中
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-8 text-center">加载中...</div>
        ) : rules.length === 0 ? (
          <div className="p-8 text-center text-gray-500">暂无规则</div>
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
                      {rule.conditions.slice(0, 2).map((c, i) => (
                        <span key={i} className="mr-1">
                          {c.field} {OPERATORS.find(o => o.value === c.operator)?.label || c.operator} {String(c.value)}
                        </span>
                      ))}
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
                      className={`px-2 py-1 text-xs rounded ${rule.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}
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
                      className="text-red-600 hover:text-red-800"
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
        />
      )}
    </div>
  )
}

function RuleModal({ rule, onClose, onSuccess }: { rule: Rule | null; onClose: () => void; onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    name: rule?.name || '',
    code: rule?.code || '',
    description: rule?.description || '',
    condition_mode: rule?.condition_mode || 'and',
    priority: rule?.priority || 0,
    conditions: rule?.conditions || [{ field: 'severity', operator: 'in', value: ['critical', 'high'] }],
    selected_channels: (rule?.actions || []).filter((a: any) => typeof a === 'number').map((a: any) => Number(a)) || [],
  })

  const { data: channels = [] } = useQuery<any[]>({
    queryKey: ['channels'],
    queryFn: () => apiClient.get('/channels', { is_active: true }),
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
    // 将选中的渠道转换为actions格式
    const actions = formData.selected_channels.map(channelId => ({
      type: 'notify',
      channels: [channelId]
    }))
    const payload = {
      name: formData.name,
      code: formData.code,
      description: formData.description,
      conditions: formData.conditions,
      condition_mode: formData.condition_mode,
      priority: formData.priority,
      actions,
    }
    if (rule) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
    }
  }

  const addCondition = () => {
    setFormData({
      ...formData,
      conditions: [...formData.conditions, { field: 'severity', operator: 'eq', value: '' }],
    })
  }

  const removeCondition = (index: number) => {
    setFormData({
      ...formData,
      conditions: formData.conditions.filter((_, i) => i !== index),
    })
  }

  const updateCondition = (index: number, field: string, value: any) => {
    const newConditions = [...formData.conditions]
    newConditions[index] = { ...newConditions[index], [field]: value }
    setFormData({ ...formData, conditions: newConditions })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-auto">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold">{rule ? '编辑规则' : '创建规则'}</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
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
              <label className="block text-sm font-medium text-gray-700 mb-1">规则代码</label>
              <input
                type="text"
                required
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
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
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">条件</label>
              <button type="button" onClick={addCondition} className="text-sm text-blue-600 hover:text-blue-800">
                + 添加条件
              </button>
            </div>
            <div className="space-y-2">
              {formData.conditions.map((condition, index) => (
                <div key={index} className="flex gap-2 items-center">
                  <select
                    value={condition.field}
                    onChange={(e) => updateCondition(index, 'field', e.target.value)}
                    className="px-2 py-1 border rounded text-sm"
                  >
                    <option value="severity">严重级别</option>
                    <option value="source">告警来源</option>
                    <option value="labels.cluster">集群</option>
                    <option value="labels.service">服务</option>
                    <option value="labels.env">环境</option>
                    <option value="metric_name">指标名称</option>
                    <option value="title">标题</option>
                    <option value="content">内容</option>
                  </select>
                  <select
                    value={condition.operator}
                    onChange={(e) => updateCondition(index, 'operator', e.target.value)}
                    className="px-2 py-1 border rounded text-sm"
                  >
                    {OPERATORS.map((op) => (
                      <option key={op.value} value={op.value}>{op.label}</option>
                    ))}
                  </select>
                  {condition.field === 'severity' ? (
                    <select
                      multiple
                      value={Array.isArray(condition.value) ? condition.value : [condition.value]}
                      onChange={(e) => updateCondition(index, 'value', Array.from(e.target.selectedOptions).map(o => o.value))}
                      className="px-2 py-1 border rounded text-sm flex-1"
                    >
                      {SEVERITY_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s.toUpperCase()}</option>
                      ))}
                    </select>
                  ) : condition.field === 'source' ? (
                    <select
                      multiple
                      value={Array.isArray(condition.value) ? condition.value : [condition.value]}
                      onChange={(e) => updateCondition(index, 'value', Array.from(e.target.selectedOptions).map(o => o.value))}
                      className="px-2 py-1 border rounded text-sm flex-1"
                    >
                      {SOURCE_OPTIONS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
                      onChange={(e) => updateCondition(index, 'value', e.target.value)}
                      placeholder="多个值用逗号分隔"
                      className="px-2 py-1 border rounded text-sm flex-1"
                    />
                  )}
                  <button
                    type="button"
                    onClick={() => removeCondition(index)}
                    className="text-red-600 hover:text-red-800"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">通知渠道</label>
            <div className="space-y-2">
              {channels.length === 0 ? (
                <div className="text-sm text-gray-500">暂无可用渠道，请先创建通知渠道</div>
              ) : (
                channels.map((channel: any) => (
                  <label key={channel.id} className="flex items-center gap-2 p-2 border rounded hover:bg-gray-50">
                    <input
                      type="checkbox"
                      checked={formData.selected_channels.includes(channel.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormData({
                            ...formData,
                            selected_channels: [...formData.selected_channels, channel.id]
                          })
                        } else {
                          setFormData({
                            ...formData,
                            selected_channels: formData.selected_channels.filter((id: number) => id !== channel.id)
                          })
                        }
                      }}
                      className="rounded"
                    />
                    <span className="font-medium">{channel.name}</span>
                    <span className="text-sm text-gray-500">({channel.channel_type})</span>
                  </label>
                ))
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
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {rule ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}