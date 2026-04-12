import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { FIELD_CONFIGS } from '@/components/condition/constants'
import { RulesLayout } from '@/components/rules/RulesLayout'
import { DedupConfigForm, dedupConfigToPayload, DEFAULT_DEDUP_CONFIG, DedupConfig } from '@/components/strategy/DedupConfigForm'

interface StrategyRule {
  id: number
  name: string
  code: string
  description?: string
  priority: number
  is_active: boolean
  conditions: Condition[]
  condition_mode: string
  config: any
  match_count: number
  last_match_at?: string
  created_at: string
  updated_at: string
}

function getDedupSummary(config: any): string {
  if (!config) return ''
  const type = config.dedup_type || 'fingerprint'
  const window = config.window_seconds || 300
  if (type === 'fingerprint') {
    const fields = (config.fingerprint_fields || ['alert_key']).join(', ')
    return `指纹模式: ${fields} / ${window}s`
  }
  return `条件模式: ${(config.conditions || []).length} 个条件 / ${window}s`
}

export function DedupRulesPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<StrategyRule | null>(null)

  const { data: rules = [], isLoading } = useQuery<StrategyRule[]>({
    queryKey: ['dedup-rules'],
    queryFn: () => apiClient.get('/rules/dedup-rules'),
  })

  const deleteMutation = useMutation({
    mutationFn: (ruleId: number) => apiClient.delete(`/rules/dedup-rules/${ruleId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dedup-rules'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ ruleId, is_active }: { ruleId: number; is_active: boolean }) =>
      apiClient.put(`/rules/dedup-rules/${ruleId}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dedup-rules'] }),
  })

  const handleEdit = (rule: StrategyRule) => {
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
          去重规则在指定时间窗口内对重复告警进行合并，支持按指纹字段或条件匹配
        </p>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-amber-600 text-white text-sm rounded-md hover:bg-amber-700"
        >
          创建去重规则
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : rules.length === 0 ? (
          <div className="p-12 text-center">
            <svg className="w-12 h-12 mx-auto text-amber-200 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 15v-1a4 4 0 00-4-4H8m0 0l3 3m-3-3l3-3m9 14V5a2 2 0 00-2-2H6a2 2 0 00-2 2v16l4-2 4 2 4-2 4 2z" />
            </svg>
            <div className="text-gray-500 font-medium">暂无去重规则</div>
            <div className="text-sm text-gray-400 mt-1">创建去重规则避免相同告警重复通知</div>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-amber-50/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-amber-700">规则名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-amber-700">去重策略</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-amber-700">触发条件</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-amber-700">优先级</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-amber-700">匹配</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-amber-700">状态</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-amber-700">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-amber-50/30">
                  <td className="px-4 py-3">
                    <div className="font-medium">{rule.name}</div>
                    {rule.description && (
                      <div className="text-sm text-gray-500">{rule.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-600">{getDedupSummary(rule.config)}</div>
                  </td>
                  <td className="px-4 py-3">
                    {rule.conditions.length > 0 ? (
                      <div className="text-sm text-gray-600">
                        {rule.conditions.length} 个条件 ({rule.condition_mode})
                      </div>
                    ) : (
                      <span className="text-sm text-gray-400">无条件（全局生效）</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-sm bg-amber-100 text-amber-800 rounded">
                      {rule.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm">{rule.match_count}</div>
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
                      className="text-amber-600 hover:text-amber-800 mr-3"
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
        <DedupRuleModal
          rule={editingRule}
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            queryClient.invalidateQueries({ queryKey: ['dedup-rules'] })
          }}
        />
      )}
    </RulesLayout>
  )
}

export function DedupRuleModal({ rule, initialConditions, onClose, onSuccess }: { rule: StrategyRule | null; initialConditions?: Condition[]; onClose: () => void; onSuccess: () => void }) {
  const [name, setName] = useState(rule?.name || '')
  const [description, setDescription] = useState(rule?.description || '')
  const [priority, setPriority] = useState(rule?.priority || 0)
  const [conditions, setConditions] = useState<Condition[]>(rule?.conditions || initialConditions || [])
  const [conditionMode, setConditionMode] = useState(rule?.condition_mode || 'and')
  const [config, setConfig] = useState<DedupConfig>(() => {
    if (rule?.config) {
      const c = rule.config
      return {
        enabled: c.enabled ?? true,
        mode: c.dedup_type ?? 'fingerprint',
        fingerprint_fields: c.fingerprint_fields ?? ['alert_key'],
        window_seconds: c.window_seconds ?? 300,
        dimensions: c.dimensions ?? { by_severity: false, by_source: false },
        strategy: c.strategy ?? 'first',
        condition_mode: c.condition_mode ?? 'and',
        conditions: c.conditions ?? [],
      }
    }
    return DEFAULT_DEDUP_CONFIG
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/rules/dedup-rules', data),
    onSuccess,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/rules/dedup-rules/${rule?.id}`, data),
    onSuccess,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload = {
      name,
      description: description || null,
      priority,
      is_active: true,
      conditions,
      condition_mode: conditionMode,
      config: dedupConfigToPayload(config),
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
        <div className="p-6 border-b border-amber-100 bg-amber-50/50">
          <h2 className="text-xl font-bold text-amber-900">{rule ? '编辑去重规则' : '创建去重规则'}</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">规则名称</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 border rounded-md"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">条件组合方式</label>
              <select
                value={conditionMode}
                onChange={(e) => setConditionMode(e.target.value)}
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
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">触发条件（可选，仅当条件满足时此规则才生效）</label>
            <ConditionEditor
              conditions={conditions}
              onChange={setConditions}
              fields={FIELD_CONFIGS}
            />
          </div>

          <div className="border-t pt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">去重配置</label>
            <DedupConfigForm config={config} onChange={setConfig} />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-amber-600 text-white rounded-md hover:bg-amber-700 disabled:opacity-50"
            >
              {rule ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
