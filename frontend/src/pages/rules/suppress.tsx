import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { FIELD_CONFIGS } from '@/components/condition/constants'
import { RulesLayout } from '@/components/rules/RulesLayout'
import {
  buildSuppressConfigPayload,
  mergeLegacySuppressConditions,
  getDurationMinutesFromConfig,
  formatEffectiveUntilLocal,
  SUPPRESS_DURATION_HELP,
  getSuppressStatusBadge,
} from '@/components/strategy/SuppressConfigForm'
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
  suppress_in_effect?: boolean | null
  created_at: string
  updated_at: string
}

function formatDurationSummary(rule: StrategyRule): string {
  const minutes = getDurationMinutesFromConfig(rule.config)
  if (minutes <= 0) return '永久'
  const until = formatEffectiveUntilLocal(rule.config?.effective_until as string | undefined)
  return until ? `${minutes} 分钟 · 至 ${until}` : `${minutes} 分钟`
}

function formatConditionSummary(rule: StrategyRule): string {
  const cond =
    rule.conditions.length === 0
      ? '无条件（匹配全部告警）'
      : `${rule.conditions.length} 个条件 (${rule.condition_mode})`
  return `${cond} · ${formatDurationSummary(rule)}`
}

export function SuppressRulesPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<StrategyRule | null>(null)

  const { data: rules = [], isLoading, isError, error } = useQuery<StrategyRule[]>({
    queryKey: ['suppress-rules'],
    queryFn: () => apiClient.get('/rules/suppress-rules'),
  })

  const deleteMutation = useMutation({
    mutationFn: (ruleId: number) => apiClient.delete(`/rules/suppress-rules/${ruleId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['suppress-rules'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ ruleId, is_active }: { ruleId: number; is_active: boolean }) =>
      apiClient.put(`/rules/suppress-rules/${ruleId}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['suppress-rules'] }),
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
          抑制规则在指定条件下静默告警，避免重复或计划内运维告警产生干扰
        </p>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-rose-600 text-white text-sm rounded-md hover:bg-rose-700"
        >
          创建抑制规则
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        {isError ? (
          <div className="p-8 text-center text-rose-600 text-sm">
            加载抑制规则失败：{(error as Error)?.message || '请刷新重试'}
          </div>
        ) : isLoading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : rules.length === 0 ? (
          <div className="p-12 text-center">
            <svg className="w-12 h-12 mx-auto text-rose-200 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            <div className="text-gray-500 font-medium">暂无抑制规则</div>
            <div className="text-sm text-gray-400 mt-1">创建抑制规则在维护期间静默告警</div>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-rose-50/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-rose-700">规则名称</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-rose-700">抑制条件</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-rose-700">优先级</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-rose-700">抑制次数</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-rose-700">状态</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-rose-700">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-rose-50/30">
                  <td className="px-4 py-3">
                    <div className="font-medium">{rule.name}</div>
                    {rule.description && (
                      <div className="text-sm text-gray-500">{rule.description}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-600">{formatConditionSummary(rule)}</div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-sm bg-rose-100 text-rose-800 rounded">
                      {rule.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm">{rule.match_count}</div>
                    {rule.last_match_at && (
                      <div className="text-xs text-gray-400">
                        最近 {new Date(rule.last_match_at).toLocaleString('zh-CN')}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {(() => {
                      const badge = getSuppressStatusBadge(rule)
                      return (
                        <div className="flex flex-col gap-1 items-start">
                          <span className={`px-2 py-1 text-xs rounded ${badge.className}`}>
                            {badge.label}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              toggleMutation.mutate({ ruleId: rule.id, is_active: !rule.is_active })
                            }
                            disabled={toggleMutation.isPending}
                            className="text-xs text-rose-600 hover:text-rose-800 disabled:opacity-50"
                          >
                            {rule.is_active ? '点击停用' : '点击启用'}
                          </button>
                        </div>
                      )
                    })()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleEdit(rule)}
                      className="text-rose-600 hover:text-rose-800 mr-3"
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
        <SuppressRuleModal
          rule={editingRule}
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            queryClient.invalidateQueries({ queryKey: ['suppress-rules'] })
          }}
        />
      )}
    </RulesLayout>
  )
}

export function SuppressRuleModal({ rule, initialConditions, onClose, onSuccess }: { rule: StrategyRule | null; initialConditions?: Condition[]; onClose: () => void; onSuccess: () => void }) {
  const [name, setName] = useState(rule?.name || '')
  const [description, setDescription] = useState(rule?.description || '')
  const [priority, setPriority] = useState(rule?.priority || 0)
  const [conditions, setConditions] = useState<Condition[]>(() => {
    if (rule) {
      return mergeLegacySuppressConditions(rule.conditions, rule.config) as Condition[]
    }
    return initialConditions || []
  })
  const [conditionMode, setConditionMode] = useState(rule?.condition_mode || 'and')
  const [durationMinutes, setDurationMinutes] = useState(() =>
    rule ? getDurationMinutesFromConfig(rule.config) : 0,
  )

  const [submitError, setSubmitError] = useState<string | null>(null)
  const effectiveUntilLabel = rule
    ? formatEffectiveUntilLocal(rule.config?.effective_until as string | undefined)
    : null

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/rules/suppress-rules', data),
    onSuccess: () => {
      setSubmitError(null)
      onSuccess()
    },
    onError: (err: Error) => {
      setSubmitError(err.message || '创建失败')
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/rules/suppress-rules/${rule?.id}`, data),
    onSuccess: () => {
      setSubmitError(null)
      onSuccess()
    },
    onError: (err: Error) => {
      setSubmitError(err.message || '保存失败')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitError(null)

    if (conditions.length === 0) {
      setSubmitError('请至少添加一条抑制条件')
      return
    }

    const payload = {
      name,
      description: description || null,
      priority,
      is_active: true,
      conditions,
      condition_mode: conditionMode,
      config: buildSuppressConfigPayload(durationMinutes),
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
      title={rule ? '编辑抑制规则' : '创建抑制规则'}
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

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">抑制时长（分钟）</label>
            <input
              type="number"
              min={0}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Math.max(0, parseInt(e.target.value, 10) || 0))}
              className="w-full px-3 py-2 border rounded-md"
            />
            <p className="text-xs text-gray-500 mt-1">0 表示永久抑制</p>
            <p className="text-xs text-gray-500 mt-1">{SUPPRESS_DURATION_HELP}</p>
            {effectiveUntilLabel && (
              <p className="text-xs text-rose-700 mt-2">
                当前生效至：{effectiveUntilLabel}（保存后将按新时长重算）
              </p>
            )}
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
            <label className="block text-sm font-medium text-gray-700 mb-1">抑制条件</label>
            <p className="text-xs text-gray-500 mb-2">
              告警满足以下条件时将被抑制（不发送通知），适用于各类告警源
            </p>
            <ConditionEditor
              conditions={conditions}
              onChange={setConditions}
              fields={FIELD_CONFIGS}
            />
          </div>

          {submitError && (
            <p className="text-sm text-rose-600 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
              {submitError}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-rose-600 text-white rounded-md hover:bg-rose-700 disabled:opacity-50"
            >
              {rule ? '保存' : '创建'}
            </button>
          </div>
        </form>
    </Modal>
  )
}
