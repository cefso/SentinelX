import { useState, useRef, useEffect, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'

export interface Condition {
  field: string
  operator: string
  value: any
  key?: string  // 用于 labels 字段的 key 传递
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
  { value: 'in', label: '在列表中' },
  { value: 'not_in', label: '不在列表中' },
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'regex', label: '正则匹配' },
  { value: 'gt', label: '大于' },
  { value: 'gte', label: '大于等于' },
  { value: 'lt', label: '小于' },
  { value: 'lte', label: '小于等于' },
  { value: 'exists', label: '存在' },
  { value: 'is_empty', label: '为空' },
]

const SEVERITY_OPTIONS = ['critical', 'high', 'medium', 'low', 'info']

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
          showModal={showModal}
        />
      )}
    </div>
  )
}

export function RuleModal({ rule, onClose, onSuccess, initialConditions, showModal }: { rule: Rule | null; onClose: () => void; onSuccess: () => void; initialConditions?: Condition[]; showModal?: boolean }) {
  // ▼ 下拉相关状态
  const [openFieldKey, setOpenFieldKey] = useState<string>('')
  const dropdownRef = useRef<HTMLDivElement | null>(null)
  const fieldValuesCache = useRef<Record<string, { data: { value: string; count: number }[]; timestamp: number }>>({})
  const [fieldValuesData, setFieldValuesData] = useState<{ value: string; count: number }[]>([])
  const [isLoadingFieldValues, setIsLoadingFieldValues] = useState(false)

  // 当 initialConditions prop 更新时，同步更新 formData.conditions
  // 解决 useState 初始化时机早于 props 更新的问题
  const [formData, setFormData] = useState({
    name: rule?.name || '',
    code: rule?.code || '',
    description: rule?.description || '',
    condition_mode: rule?.condition_mode || 'and',
    priority: rule?.priority || 0,
    conditions: rule?.conditions || initialConditions || [{ field: 'severity', operator: 'in', value: ['critical'] }],
    selected_channels: (rule?.actions || []).filter((a: any) => typeof a === 'number').map((a: any) => Number(a)) || [],
  })

  // labels 字段当前选中的 key（用于 Key+Value 下拉框）
  // 使用 useMemo 从 formData.conditions 派生，确保始终同步
  const labelsKey = useMemo(() => {
    const result: Record<number, string> = {}
    formData.conditions.forEach((cond: any, idx: number) => {
      if (cond.field === 'labels' && cond.key) {
        result[idx] = cond.key
      }
    })
    return result
  }, [formData.conditions])

  // 预加载字段值（modal 打开时自动加载）
  useEffect(() => {
    if (showModal) {
      ;['namespace', 'instance_id', 'instance_name', 'metric_name', 'labels'].forEach(field => {
        fetchFieldValues(field)
      })
      // 为 initialConditions 中已有的 labels.{key} 预加载值
      if (initialConditions && initialConditions.length > 0) {
        initialConditions.forEach((cond: any) => {
          if (cond.field === 'labels' && cond.key) {
            fetchFieldValues(`labels.${cond.key}`)
          }
        })
      }
    }
  }, [showModal, initialConditions])

  // 点击外部关闭下拉
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpenFieldKey('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const fetchFieldValues = async (field: string) => {
    const now = Date.now()
    const cached = fieldValuesCache.current[field]
    if (cached && now - cached.timestamp < 60000) {
      setFieldValuesData(cached.data)
      return
    }
    setIsLoadingFieldValues(true)
    try {
      const result = await apiClient.getRuleFieldValues({ field, limit: 50 })
      fieldValuesCache.current[field] = { data: result.values, timestamp: now }
      setFieldValuesData(result.values)
    } finally {
      setIsLoadingFieldValues(false)
    }
  }

  const toggleFieldValuesDropdown = (index: number, field: string) => {
    const key = `${index}-${field}`
    if (openFieldKey === key) {
      setOpenFieldKey('')
    } else {
      setOpenFieldKey(key)
      fetchFieldValues(field)
    }
  }

  // 监听 initialConditions 变化：当从空变为有值时，同步更新 formData.conditions
  // labelsKey 通过 useMemo 从 formData.conditions 派生，无需单独同步
  const prevConditionsJsonRef = useRef<string>('')
  useEffect(() => {
    const json = JSON.stringify(initialConditions)
    if (json !== prevConditionsJsonRef.current && initialConditions && initialConditions.length > 0) {
      prevConditionsJsonRef.current = json
      setFormData((prev) => ({
        ...prev,
        conditions: initialConditions,
      }))
    }
  }, [initialConditions])

  const { data: channels = [] } = useQuery<any[]>({
    queryKey: ['channels'],
    queryFn: () => apiClient.get('/channels', { is_active: true }),
  })

  const { data: sources = [] } = useQuery<any[]>({
    queryKey: ['alert-sources'],
    queryFn: () => apiClient.get('/sources'),
  })

  const { data: users = [] } = useQuery<any[]>({
    queryKey: ['users'],
    queryFn: () => apiClient.get('/users'),
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
      conditions: [...formData.conditions, { field: 'severity', operator: 'in', value: ['critical'] }],
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
          <h2 className="text-xl font-bold">{rule ? '编辑规则' : initialConditions ? '快捷创建规则' : '创建规则'}</h2>
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
                    onChange={(e) => {
                      const newField = e.target.value
                      setFormData((prev) => {
                        const conditions = prev.conditions.map((c, i) => {
                          if (i !== index) return c
                          // 如果之前是 labels.xxx，现在变成其他，重置 condition.key
                          if (c.field.startsWith('labels.') && !newField.startsWith('labels.')) {
                            const { key, ...rest } = c
                            return { ...rest, field: newField, value: '' }
                          }
                          return { ...c, field: newField, value: '' }
                        })
                        return { ...prev, conditions }
                      })
                    }}
                    className="px-2 py-1 border rounded text-sm"
                  >
                    <option value="severity">严重级别</option>
                    <option value="source">告警来源</option>
                    <option value="namespace">命名空间</option>
                    <option value="instance_id">实例ID</option>
                    <option value="instance_name">实例名称</option>
                    <option value="status">状态</option>
                    <option value="fire_count">触发次数</option>
                    <option value="repeat_count">重复次数</option>
                    <option value="escalation_count">升级次数</option>
                    <option value="assignee">处理人</option>
                    <option value="labels">标签</option>
                    <option value="metric_name">指标</option>
                    <option value="title">标题</option>
                    <option value="content">内容</option>
                  </select>
                  <select
                    value={condition.operator}
                    onChange={(e) => {
                      const newOperator = e.target.value
                      setFormData((prev) => {
                        const conditions = prev.conditions.map((c, i) => {
                          if (i !== index) return c
                          let newValue: string | string[] = ''
                          if (['in', 'not_in'].includes(newOperator)) {
                            // 切换到数组操作符：字符串转数组
                            if (typeof c.value === 'string' && c.value) {
                              newValue = c.value.split(',').map(v => v.trim()).filter(v => v)
                            } else if (Array.isArray(c.value)) {
                              newValue = c.value
                            } else {
                              newValue = []
                            }
                          } else if (['exists', 'is_empty'].includes(newOperator)) {
                            newValue = ''
                          } else {
                            // 切换到字符串操作符：数组转字符串
                            if (Array.isArray(c.value) && c.value.length > 0) {
                              newValue = c.value[0] || ''
                            } else if (Array.isArray(c.value)) {
                              newValue = ''
                            } else {
                              newValue = c.value || ''
                            }
                          }
                          return { ...c, operator: newOperator, value: newValue }
                        })
                        return { ...prev, conditions }
                      })
                    }}
                    className="px-2 py-1 border rounded text-sm"
                  >
                    {OPERATORS.map((op) => (
                      <option key={op.value} value={op.value}>{op.label}</option>
                    ))}
                  </select>
                  {['exists', 'is_empty'].includes(condition.operator) ? (
                    <span className="text-gray-400 text-sm flex-1 px-2 py-1">无需输入值</span>
                  ) : ['in', 'not_in'].includes(condition.operator) ? (
                    condition.field === 'severity' ? (
                      <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
                        {SEVERITY_OPTIONS.map((s) => {
                          const checked = Array.isArray(condition.value) ? condition.value.includes(s) : condition.value === s
                          return (
                            <label key={s} className="flex items-center gap-1.5 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => {
                                  const current = Array.isArray(condition.value) ? condition.value : []
                                  if (checked) {
                                    updateCondition(index, 'value', current.filter((v: string) => v !== s))
                                  } else {
                                    updateCondition(index, 'value', [...current, s])
                                  }
                                }}
                                className="w-4 h-4"
                              />
                              <span className="text-sm">{s.toUpperCase()}</span>
                            </label>
                          )
                        })}
                      </div>
                    ) : condition.field === 'source' ? (
                      <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
                        {sources.map((s: any) => {
                          const checked = Array.isArray(condition.value)
                            ? condition.value.includes(s.source_type)
                            : condition.value === s.source_type
                          return (
                            <label key={s.id} className="flex items-center gap-1.5 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => {
                                  const current = Array.isArray(condition.value) ? condition.value : []
                                  if (checked) {
                                    updateCondition(index, 'value', current.filter((v: string) => v !== s.source_type))
                                  } else {
                                    updateCondition(index, 'value', [...current, s.source_type])
                                  }
                                }}
                                className="w-4 h-4"
                              />
                              <span className="text-sm">{s.name}</span>
                            </label>
                          )
                        })}
                      </div>
                    ) : condition.field === 'status' ? (
                      <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
                        {['firing', 'resolved', 'suppressed', 'acknowledged'].map((s) => {
                          const checked = Array.isArray(condition.value)
                            ? condition.value.includes(s)
                            : condition.value === s
                          return (
                            <label key={s} className="flex items-center gap-1.5 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => {
                                  const current = Array.isArray(condition.value) ? condition.value : []
                                  if (checked) {
                                    updateCondition(index, 'value', current.filter((v: string) => v !== s))
                                  } else {
                                    updateCondition(index, 'value', [...current, s])
                                  }
                                }}
                                className="w-4 h-4"
                              />
                              <span className="text-sm">{s === 'firing' ? '触发中' : s === 'resolved' ? '已恢复' : s === 'suppressed' ? '已抑制' : '已确认'}</span>
                            </label>
                          )
                        })}
                      </div>
                    ) : condition.field === 'assignee' ? (
                      <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
                        {users.map((u: any) => {
                          const checked = Array.isArray(condition.value)
                            ? condition.value.includes(String(u.id))
                            : condition.value === String(u.id)
                          return (
                            <label key={u.id} className="flex items-center gap-1.5 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={() => {
                                  const current = Array.isArray(condition.value) ? condition.value : []
                                  if (checked) {
                                    updateCondition(index, 'value', current.filter((v: string) => v !== String(u.id)))
                                  } else {
                                    updateCondition(index, 'value', [...current, String(u.id)])
                                  }
                                }}
                                className="w-4 h-4"
                              />
                              <span className="text-sm">{u.username}</span>
                            </label>
                          )
                        })}
                      </div>
                    ) : ['namespace', 'instance_id', 'instance_name', 'metric_name'].includes(condition.field) ? (
                      <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
                        {(() => {
                          // 获取该字段的缓存数据
                          const cached = fieldValuesCache.current[condition.field]
                          if (!cached || cached.data.length === 0) {
                            // 缓存为空，显示加载中
                            return (
                              <span className="text-sm text-gray-500">加载中...</span>
                            )
                          }
                          return cached.data.map((item) => {
                            const checked = Array.isArray(condition.value) ? condition.value.includes(item.value) : condition.value === item.value
                            return (
                              <label key={item.value} className="flex items-center gap-1.5 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => {
                                    const current = Array.isArray(condition.value) ? condition.value : []
                                    if (checked) {
                                      updateCondition(index, 'value', current.filter((v: string) => v !== item.value))
                                    } else {
                                      updateCondition(index, 'value', [...current, item.value])
                                    }
                                  }}
                                  className="w-4 h-4"
                                />
                                <span className="text-sm">{item.value}</span>
                              </label>
                            )
                          })
                        })()}
                      </div>
                    ) : (
                      <input
                        type="text"
                        value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
                        onChange={(e) => updateCondition(index, 'value', e.target.value)}
                        placeholder="多个值用逗号分隔"
                        className="px-2 py-1 border rounded text-sm flex-1"
                      />
                    )
                  ) : ['eq', 'ne'].includes(condition.operator) ? (
                    condition.field === 'severity' ? (
                      <select
                        value={Array.isArray(condition.value) ? condition.value[0] : condition.value}
                        onChange={(e) => updateCondition(index, 'value', e.target.value)}
                        className="px-2 py-1 border rounded text-sm flex-1"
                      >
                        <option value="">全部</option>
                        {SEVERITY_OPTIONS.map((s) => (
                          <option key={s} value={s}>{s.toUpperCase()}</option>
                        ))}
                      </select>
                    ) : condition.field === 'source' ? (
                      <select
                        value={Array.isArray(condition.value) ? condition.value[0] : condition.value}
                        onChange={(e) => updateCondition(index, 'value', e.target.value)}
                        className="px-2 py-1 border rounded text-sm flex-1"
                      >
                        <option value="">全部</option>
                        {sources.map((s: any) => (
                          <option key={s.id} value={s.source_type}>{s.name}</option>
                        ))}
                      </select>
                    ) : condition.field === 'status' ? (
                      <select
                        value={Array.isArray(condition.value) ? condition.value[0] : condition.value}
                        onChange={(e) => updateCondition(index, 'value', e.target.value)}
                        className="px-2 py-1 border rounded text-sm flex-1"
                      >
                        <option value="">全部</option>
                        <option value="firing">触发中</option>
                        <option value="resolved">已恢复</option>
                        <option value="suppressed">已抑制</option>
                        <option value="acknowledged">已确认</option>
                      </select>
                    ) : condition.field === 'assignee' ? (
                      <select
                        value={Array.isArray(condition.value) ? condition.value[0] : condition.value}
                        onChange={(e) => updateCondition(index, 'value', e.target.value)}
                        className="px-2 py-1 border rounded text-sm flex-1"
                      >
                        <option value="">全部</option>
                        {users.map((u: any) => (
                          <option key={u.id} value={String(u.id)}>{u.username}</option>
                        ))}
                      </select>
                    ) : condition.field === 'labels' && !['exists', 'is_empty'].includes(condition.operator) ? (
                      <div className="relative flex-1 flex gap-1 items-center">
                        {/* Key 下拉框 */}
                        <select
                          value={labelsKey[index] || ''}
                          onChange={(e) => {
                            const key = e.target.value
                            // 设置 condition.key 以同步 labelsKey (useMemo)
                            updateCondition(index, 'key', key)
                            // 选择 key 后更新 field 为 labels.{key}，并加载对应的 values
                            updateCondition(index, 'field', key ? `labels.${key}` : 'labels')
                            updateCondition(index, 'value', '')
                            if (key) {
                              fetchFieldValues(`labels.${key}`)
                            }
                          }}
                          className="px-2 py-1 border rounded text-sm w-28"
                        >
                          <option value="">选择标签键</option>
                          {(() => {
                            const cached = fieldValuesCache.current['labels']
                            if (!cached?.data?.length) {
                              return <option disabled>加载中...</option>
                            }
                            return cached.data.map((item: any) => (
                              <option key={item.value} value={item.value}>{item.value}</option>
                            ))
                          })()}
                        </select>

                        {/* Value 下拉框（根据 selected key 动态加载） */}
                        <select
                          value={condition.value}
                          onChange={(e) => updateCondition(index, 'value', e.target.value)}
                          disabled={!labelsKey[index]}
                          className="px-2 py-1 border rounded text-sm flex-1"
                        >
                          <option value="">选择标签值</option>
                          {labelsKey[index] && (() => {
                            const cached = fieldValuesCache.current[`labels.${labelsKey[index]}`]
                            if (!cached?.data?.length) {
                              return <option disabled>加载中...</option>
                            }
                            return cached.data.map((item: any) => (
                              <option key={item.value} value={item.value}>{item.value} ({item.count})</option>
                            ))
                          })()}
                        </select>
                      </div>
                    ) : ['namespace', 'instance_id', 'instance_name', 'metric_name'].includes(condition.field) ? (
                      <div className="relative flex-1 flex gap-1" ref={dropdownRef}>
                        <input
                          type="text"
                          value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
                          onChange={(e) => updateCondition(index, 'value', e.target.value)}
                          placeholder="输入值"
                          className="px-2 py-1 border rounded text-sm flex-1"
                        />
                        <button
                          type="button"
                          onClick={() => toggleFieldValuesDropdown(index, condition.field)}
                          className="px-1.5 border rounded text-gray-500 hover:bg-gray-50 text-sm"
                          title="获取可选值"
                        >
                          ▼
                        </button>
                        {openFieldKey === `${index}-${condition.field}` && (
                          <div className="absolute z-10 top-full left-0 mt-1 w-64 max-h-60 overflow-y-auto bg-white border rounded shadow-lg">
                            {isLoadingFieldValues ? (
                              <div className="px-3 py-2 text-sm text-gray-500">加载中...</div>
                            ) : fieldValuesData.length === 0 ? (
                              <div className="px-3 py-2 text-sm text-gray-500">无可选值</div>
                            ) : (
                              fieldValuesData.map((item) => (
                                <button
                                  key={item.value}
                                  type="button"
                                  onClick={() => {
                                    updateCondition(index, 'value', item.value)
                                    setOpenFieldKey('')
                                  }}
                                  className="w-full px-3 py-1.5 text-left text-sm hover:bg-gray-100 truncate"
                                >
                                  {item.value} <span className="text-gray-400 text-xs">({item.count})</span>
                                </button>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <input
                        type="text"
                        value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
                        onChange={(e) => updateCondition(index, 'value', e.target.value)}
                        placeholder="输入值"
                        className="px-2 py-1 border rounded text-sm flex-1"
                      />
                    )
                  ) : condition.field === 'labels' && !['exists', 'is_empty'].includes(condition.operator) ? (
                    <div className="relative flex-1 flex gap-1 items-center">
                      {/* Key 下拉框 */}
                      <select
                        value={labelsKey[index] || ''}
                        onChange={(e) => {
                          const key = e.target.value
                          // 设置 condition.key 以同步 labelsKey (useMemo)
                          updateCondition(index, 'key', key)
                          updateCondition(index, 'field', key ? `labels.${key}` : 'labels')
                          updateCondition(index, 'value', '')
                          if (key) {
                            fetchFieldValues(`labels.${key}`)
                          }
                        }}
                        className="px-2 py-1 border rounded text-sm w-28"
                      >
                        <option value="">选择标签键</option>
                        {(() => {
                          const cached = fieldValuesCache.current['labels']
                          if (!cached?.data?.length) {
                            return <option disabled>加载中...</option>
                          }
                          return cached.data.map((item: any) => (
                            <option key={item.value} value={item.value}>{item.value}</option>
                          ))
                        })()}
                      </select>

                      {/* Value 下拉框（根据 selected key 动态加载） */}
                      <select
                        value={condition.value}
                        onChange={(e) => updateCondition(index, 'value', e.target.value)}
                        disabled={!labelsKey[index]}
                        className="px-2 py-1 border rounded text-sm flex-1"
                      >
                        <option value="">选择标签值</option>
                        {labelsKey[index] && (() => {
                          const cached = fieldValuesCache.current[`labels.${labelsKey[index]}`]
                          if (!cached?.data?.length) {
                            return <option disabled>加载中...</option>
                          }
                          return cached.data.map((item: any) => (
                            <option key={item.value} value={item.value}>{item.value} ({item.count})</option>
                          ))
                        })()}
                      </select>
                    </div>
                  ) : ['namespace', 'instance_id', 'instance_name', 'metric_name'].includes(condition.field) ? (
                    <div className="relative flex-1 flex gap-1" ref={dropdownRef}>
                      <input
                        type="text"
                        value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
                        onChange={(e) => updateCondition(index, 'value', e.target.value)}
                        placeholder="输入值"
                        className="px-2 py-1 border rounded text-sm flex-1"
                      />
                      <button
                        type="button"
                        onClick={() => toggleFieldValuesDropdown(index, condition.field)}
                        className="px-1.5 border rounded text-gray-500 hover:bg-gray-50 text-sm"
                        title="获取可选值"
                      >
                        ▼
                      </button>
                      {openFieldKey === `${index}-${condition.field}` && (
                        <div className="absolute z-10 top-full left-0 mt-1 w-64 max-h-60 overflow-y-auto bg-white border rounded shadow-lg">
                          {isLoadingFieldValues ? (
                            <div className="px-3 py-2 text-sm text-gray-500">加载中...</div>
                          ) : fieldValuesData.length === 0 ? (
                            <div className="px-3 py-2 text-sm text-gray-500">无可选值</div>
                          ) : (
                            fieldValuesData.map((item) => (
                              <button
                                key={item.value}
                                type="button"
                                onClick={() => {
                                  updateCondition(index, 'value', item.value)
                                  setOpenFieldKey('')
                                }}
                                className="w-full px-3 py-1.5 text-left text-sm hover:bg-gray-100 truncate"
                              >
                                {item.value} <span className="text-gray-400 text-xs">({item.count})</span>
                              </button>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <input
                      type="text"
                      value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
                      onChange={(e) => updateCondition(index, 'value', e.target.value)}
                      placeholder="输入值"
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