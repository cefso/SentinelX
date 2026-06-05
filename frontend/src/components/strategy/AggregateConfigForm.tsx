import { useState } from 'react'
import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { DEDUP_AGG_FIELD_CONFIGS } from '@/components/condition/constants'

export interface AggregateConfig {
  enabled: boolean
  mode: 'group_by' | 'condition'
  window_seconds: number
  group_by: string[]
  max_count: number
  store_original_alerts: boolean
  notify_policy: 'parent_only' | 'rollup' | 'all'
  condition_mode: string
  conditions: Condition[]
}

interface AggregateConfigFormProps {
  config: AggregateConfig
  onChange: (config: AggregateConfig) => void
  onModeChange?: (mode: AggregateConfig['mode']) => void
}

const STANDARD_GROUP_BY_FIELDS = [
  'source',
  'alert_key',
  'fingerprint',
  'severity',
  'namespace',
  'instance_id',
  'metric_name',
]

/** 编辑旧规则时合并曾写在错误层级的条件 */
function normalizeAggregateConditionField(condition: Condition): Condition {
  const { field, operator, value } = condition
  if (field !== 'source' || !operator || !['in', 'not_in', 'eq', 'ne'].includes(operator)) {
    return condition
  }
  const looksLikeId = (v: unknown) => typeof v === 'number' || (typeof v === 'string' && /^\d+$/.test(v))
  if (Array.isArray(value) ? value.every(looksLikeId) : looksLikeId(value)) {
    return { ...condition, field: 'source_id' }
  }
  return condition
}

export function mergeLegacyAggregateConditions(
  ruleConditions: Condition[],
  apiConfig: Record<string, unknown> | null | undefined,
  mode: AggregateConfig['mode'],
): { ruleConditions: Condition[]; configConditions: Condition[]; configConditionMode: string } {
  const configConditions = (apiConfig?.conditions as Condition[] | undefined) || []
  const configConditionMode = (apiConfig?.condition_mode as string | undefined) || 'and'

  if (mode === 'condition') {
    if (configConditions.length > 0) {
      return {
        ruleConditions: [],
        configConditions: configConditions.map(normalizeAggregateConditionField),
        configConditionMode,
      }
    }
    if (ruleConditions.length > 0) {
      return {
        ruleConditions: [],
        configConditions: ruleConditions.map(normalizeAggregateConditionField),
        configConditionMode: 'and',
      }
    }
    return { ruleConditions: [], configConditions: [], configConditionMode }
  }

  if (ruleConditions.length > 0) {
    return { ruleConditions, configConditions: [], configConditionMode }
  }
  if (configConditions.length > 0) {
    return { ruleConditions: configConditions, configConditions: [], configConditionMode }
  }
  return { ruleConditions: [], configConditions: [], configConditionMode }
}

export function buildAggregateConfigFromApi(apiConfig: Record<string, unknown> | null | undefined): AggregateConfig {
  if (!apiConfig) return DEFAULT_AGGREGATE_CONFIG
  return {
    enabled: (apiConfig.enabled as boolean | undefined) ?? true,
    mode: (apiConfig.mode as AggregateConfig['mode']) ?? 'group_by',
    window_seconds: (apiConfig.window_seconds as number | undefined) ?? 300,
    group_by: (apiConfig.group_by as string[] | undefined) ?? ['alert_key', 'source'],
    max_count: (apiConfig.max_count as number | undefined) ?? 100,
    store_original_alerts: (apiConfig.store_original_alerts as boolean | undefined) ?? true,
    notify_policy: (apiConfig.notify_policy as AggregateConfig['notify_policy']) ?? 'parent_only',
    condition_mode: (apiConfig.condition_mode as string | undefined) ?? 'and',
    conditions: (apiConfig.conditions as Condition[] | undefined) ?? [],
  }
}

function getCustomLabelFields(groupBy: string[]): string[] {
  return groupBy.filter((f) => f.startsWith('labels.') && !STANDARD_GROUP_BY_FIELDS.includes(f))
}

export function AggregateConfigForm({ config, onChange, onModeChange }: AggregateConfigFormProps) {
  const [labelInput, setLabelInput] = useState('')
  const customLabelFields = getCustomLabelFields(config.group_by)

  const update = (partial: Partial<AggregateConfig>) => {
    onChange({ ...config, ...partial })
  }

  const setMode = (mode: AggregateConfig['mode']) => {
    if (onModeChange) {
      onModeChange(mode)
    } else {
      update({ mode })
    }
  }

  const addLabelField = () => {
    const raw = labelInput.trim()
    if (!raw) return
    const field = raw.startsWith('labels.') ? raw : `labels.${raw}`
    if (config.group_by.includes(field)) {
      setLabelInput('')
      return
    }
    update({ group_by: [...config.group_by, field] })
    setLabelInput('')
  }

  const removeLabelField = (field: string) => {
    update({ group_by: config.group_by.filter((f) => f !== field) })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600 w-20">窗口时间:</span>
        <input
          type="number"
          value={config.window_seconds}
          onChange={(e) => update({ window_seconds: parseInt(e.target.value) || 0 })}
          className="px-2 py-1 border rounded text-sm w-24"
        />
        <span className="text-sm text-gray-500">秒</span>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600 w-20">匹配模式:</span>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="agg-mode"
            checked={config.mode === 'group_by'}
            onChange={() => setMode('group_by')}
          />
          <span className="text-sm">分组模式</span>
        </label>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="agg-mode"
            checked={config.mode === 'condition'}
            onChange={() => setMode('condition')}
          />
          <span className="text-sm">条件模式</span>
        </label>
      </div>

      {config.mode === 'group_by' && (
        <div className="space-y-2">
          <p className="text-sm text-gray-500">
            相同分组字段值的告警在时间窗口内归入同一聚合组
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600 w-20">分组字段:</span>
            {STANDARD_GROUP_BY_FIELDS.map((field) => (
              <label key={field} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={config.group_by.includes(field)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      update({ group_by: [...config.group_by, field] })
                    } else {
                      update({ group_by: config.group_by.filter((f) => f !== field) })
                    }
                  }}
                />
                <span className="text-sm">{field}</span>
              </label>
            ))}
          </div>
          <div className="flex items-center gap-2 flex-wrap pl-20">
            <span className="text-sm text-gray-600">标签字段:</span>
            <input
              type="text"
              value={labelInput}
              onChange={(e) => setLabelInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  addLabelField()
                }
              }}
              placeholder="如 cluster 或 labels.env"
              className="px-2 py-1 border rounded text-sm w-48"
            />
            <button
              type="button"
              onClick={addLabelField}
              className="px-2 py-1 text-sm border rounded hover:bg-gray-50"
            >
              添加
            </button>
            {customLabelFields.map((field) => (
              <span
                key={field}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-sm bg-violet-50 text-violet-800 rounded"
              >
                {field}
                <button
                  type="button"
                  onClick={() => removeLabelField(field)}
                  className="text-violet-500 hover:text-violet-700"
                  aria-label={`移除 ${field}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      {config.mode === 'condition' && (
        <div className="space-y-2">
          <p className="text-sm text-gray-500">
            满足以下条件的告警在窗口内共用一个聚合桶
          </p>
          <ConditionEditor
            conditions={config.conditions}
            onChange={(conditions) => update({ conditions })}
            fields={DEDUP_AGG_FIELD_CONFIGS}
            conditionMode={config.condition_mode}
            onConditionModeChange={(mode) => update({ condition_mode: mode })}
          />
        </div>
      )}

      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600 w-20">最大数量:</span>
        <input
          type="number"
          value={config.max_count}
          onChange={(e) => update({ max_count: parseInt(e.target.value) || 0 })}
          className="px-2 py-1 border rounded text-sm w-24"
        />
      </div>

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={config.store_original_alerts}
          onChange={(e) => update({ store_original_alerts: e.target.checked })}
        />
        <span className="text-sm">保留原始告警（组成员可查询）</span>
      </label>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-gray-600 w-20">通知策略:</span>
        {[
          { value: 'parent_only' as const, label: '仅首条' },
          { value: 'rollup' as const, label: '汇总更新' },
          { value: 'all' as const, label: '全部通知' },
        ].map((opt) => (
          <label key={opt.value} className="flex items-center gap-1">
            <input
              type="radio"
              name="agg-notify-policy"
              checked={config.notify_policy === opt.value}
              onChange={() => update({ notify_policy: opt.value })}
            />
            <span className="text-sm">{opt.label}</span>
          </label>
        ))}
      </div>
    </div>
  )
}

export function aggregateConfigToPayload(config: AggregateConfig): any {
  const payload: any = {
    enabled: true,
    mode: config.mode,
    window_seconds: config.window_seconds,
    max_count: config.max_count,
    store_original_alerts: config.store_original_alerts,
    notify_policy: config.notify_policy,
  }
  if (config.mode === 'group_by') {
    payload.group_by = config.group_by
  } else {
    payload.conditions = config.conditions
    payload.condition_mode = config.condition_mode
  }
  return payload
}

export const DEFAULT_AGGREGATE_CONFIG: AggregateConfig = {
  enabled: true,
  mode: 'group_by',
  window_seconds: 300,
  group_by: ['alert_key', 'source'],
  max_count: 100,
  store_original_alerts: true,
  notify_policy: 'parent_only',
  condition_mode: 'and',
  conditions: [],
}
