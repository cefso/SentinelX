import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { FIELD_CONFIGS } from '@/components/condition/constants'
import { RulesLayout } from '@/components/rules/RulesLayout'
import {
  AggregateConfigForm,
  aggregateConfigToPayload,
  DEFAULT_AGGREGATE_CONFIG,
  AggregateConfig,
  mergeLegacyAggregateConditions,
  buildAggregateConfigFromApi,
} from '@/components/strategy/AggregateConfigForm'
import { Modal } from '@/components/common/Modal'

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

function getAggregateSummary(config: any): string {
  if (!config) return ''
  const mode = config.mode || 'group_by'
  const window = config.window_seconds || 300
  const max = config.max_count ?? 100
  const store = config.store_original_alerts !== false ? '保留成员' : '不保留成员'
  if (mode === 'group_by') {
    const fields = (config.group_by || []).join(', ') || 'source, fingerprint（后端默认）'
    return `分组: ${fields} / ${window}s / 最多${max}条 / ${store}`
  }
  return `条件: ${(config.conditions || []).length} 个 / ${window}s / 最多${max}条 / ${store}`
}

function getTriggerConditionSummary(rule: StrategyRule): string {
  const type = rule.config?.mode || 'group_by'
  if (type === 'condition') {
    const count = (rule.config?.conditions || []).length
    return count > 0 ? `见聚合配置（${count} 个条件）` : '见聚合配置（无条件）'
  }
  if (rule.conditions.length > 0) {
    return `${rule.conditions.length} 个条件 (${rule.condition_mode})`
  }
  return '无条件（全局生效）'
}

function initAggregateModalState(rule: StrategyRule | null, initialConditions?: Condition[]) {
  if (rule) {
    const baseConfig = buildAggregateConfigFromApi(rule.config)
    const merged = mergeLegacyAggregateConditions(rule.conditions, rule.config, baseConfig.mode)
    return {
      conditions: merged.ruleConditions,
      conditionMode: rule.condition_mode || 'and',
      config: {
        ...baseConfig,
        conditions: merged.configConditions,
        condition_mode: merged.configConditionMode || baseConfig.condition_mode,
      },
    }
  }
  return {
    conditions: initialConditions || [],
    conditionMode: 'and',
    config: DEFAULT_AGGREGATE_CONFIG,
  }
}

export function AggregateRulesPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<StrategyRule | null>(null)

  const { data: rules = [], isLoading } = useQuery<StrategyRule[]>({
    queryKey: ['aggregate-rules'],
    queryFn: () => apiClient.get('/rules/aggregate-rules'),
  })

  const deleteMutation = useMutation({
    mutationFn: (ruleId: number) => apiClient.delete(`/rules/aggregate-rules/${ruleId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['aggregate-rules'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ ruleId, is_active }: { ruleId: number; is_active: boolean }) =>
      apiClient.put(`/rules/aggregate-rules/${ruleId}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['aggregate-rules'] }),
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
          策略聚合规则在时间窗口内将相似告警合并为组，子告警默认不再重复通知
        </p>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-violet-600 text-white text-sm rounded-md hover:bg-violet-700"
        >
          创建聚合规则
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : rules.length === 0 ? (
          <div className="p-12 text-center">
            <svg className="w-12 h-12 mx-auto text-violet-200 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <div className="text-gray-500 font-medium">暂无聚合规则</div>
            <div className="text-sm text-gray-400 mt-1">创建聚合规则合并相似告警减少噪音</div>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-violet-50/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-violet-700">规则名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-violet-700">聚合策略</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-violet-700">触发条件</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-violet-700">优先级</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-violet-700">匹配</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-violet-700">状态</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-violet-700">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-violet-50/30">
                  <td className="px-4 py-3">
                    <div className="font-medium">{rule.name}</div>
                    {rule.description && (
                      <div className="text-sm text-gray-500">{rule.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-600">{getAggregateSummary(rule.config)}</div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-600">{getTriggerConditionSummary(rule)}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-sm bg-violet-100 text-violet-800 rounded">
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
                      className="text-violet-600 hover:text-violet-800 mr-3"
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
        <AggregateRuleModal
          rule={editingRule}
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            queryClient.invalidateQueries({ queryKey: ['aggregate-rules'] })
          }}
        />
      )}
    </RulesLayout>
  )
}

export function AggregateRuleModal({ rule, initialConditions, onClose, onSuccess }: { rule: StrategyRule | null; initialConditions?: Condition[]; onClose: () => void; onSuccess: () => void }) {
  const initial = initAggregateModalState(rule, initialConditions)
  const [name, setName] = useState(rule?.name || '')
  const [description, setDescription] = useState(rule?.description || '')
  const [priority, setPriority] = useState(rule?.priority || 0)
  const [conditions, setConditions] = useState<Condition[]>(initial.conditions)
  const [conditionMode, setConditionMode] = useState(initial.conditionMode)
  const [config, setConfig] = useState<AggregateConfig>(initial.config)

  const isGroupByMode = config.mode === 'group_by'

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/rules/aggregate-rules', data),
    onSuccess,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/rules/aggregate-rules/${rule?.id}`, data),
    onSuccess,
  })

  const handleModeChange = (mode: AggregateConfig['mode']) => {
    if (mode === 'condition') {
      setConfig((prev) => ({
        ...prev,
        mode,
        conditions: prev.conditions.length > 0 ? prev.conditions : conditions,
        condition_mode: prev.conditions.length > 0 ? prev.condition_mode : conditionMode,
      }))
    } else if (mode === 'group_by' && config.conditions.length > 0 && conditions.length === 0) {
      setConditions(config.conditions)
      setConditionMode(config.condition_mode)
      setConfig((prev) => ({ ...prev, mode, conditions: [], condition_mode: 'and' }))
    } else {
      setConfig((prev) => ({ ...prev, mode }))
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload = isGroupByMode
      ? {
          name,
          description: description || null,
          priority,
          is_active: true,
          conditions,
          condition_mode: conditionMode,
          config: aggregateConfigToPayload(config),
        }
      : {
          name,
          description: description || null,
          priority,
          is_active: true,
          conditions: [],
          condition_mode: 'and',
          config: aggregateConfigToPayload(config),
        }
    if (rule) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
    }
  }

  return (
    <Modal
      open={true}
      onOpenChange={(open) => { if (!open) onClose() }}
      title={rule ? '编辑聚合规则' : '创建聚合规则'}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
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

          <div className={`grid gap-4 ${isGroupByMode ? 'grid-cols-2' : 'grid-cols-1'}`}>
            {isGroupByMode && (
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
            )}
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

          {isGroupByMode && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">触发条件（可选，仅当条件满足时此规则才生效）</label>
              <ConditionEditor
                conditions={conditions}
                onChange={setConditions}
                fields={FIELD_CONFIGS}
              />
            </div>
          )}

          <div className="border-t pt-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">聚合配置</label>
            <AggregateConfigForm config={config} onChange={setConfig} onModeChange={handleModeChange} />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-violet-600 text-white rounded-md hover:bg-violet-700 disabled:opacity-50"
            >
              {rule ? '保存' : '创建'}
            </button>
          </div>
        </form>
    </Modal>
  )
}
