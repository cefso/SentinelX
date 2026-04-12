import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { DEDUP_AGG_FIELD_CONFIGS } from '@/components/condition/constants'

export interface AggregateConfig {
  enabled: boolean
  mode: 'group_by' | 'condition'
  window_seconds: number
  group_by: string[]
  max_count: number
  store_original_alerts: boolean
  condition_mode: string
  conditions: Condition[]
}

interface AggregateConfigFormProps {
  config: AggregateConfig
  onChange: (config: AggregateConfig) => void
}

export function AggregateConfigForm({ config, onChange }: AggregateConfigFormProps) {
  const update = (partial: Partial<AggregateConfig>) => {
    onChange({ ...config, ...partial })
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
            onChange={() => update({ mode: 'group_by' })}
          />
          <span className="text-sm">分组模式</span>
        </label>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="agg-mode"
            checked={config.mode === 'condition'}
            onChange={() => update({ mode: 'condition' })}
          />
          <span className="text-sm">条件模式</span>
        </label>
      </div>

      {config.mode === 'group_by' && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-gray-600 w-20">分组字段:</span>
          {['source', 'alert_key', 'severity', 'namespace', 'instance_id', 'metric_name'].map((field) => (
            <label key={field} className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={config.group_by.includes(field)}
                onChange={(e) => {
                  if (e.target.checked) {
                    update({ group_by: [...config.group_by, field] })
                  } else {
                    update({ group_by: config.group_by.filter(f => f !== field) })
                  }
                }}
              />
              <span className="text-sm">{field}</span>
            </label>
          ))}
        </div>
      )}

      {config.mode === 'condition' && (
        <ConditionEditor
          conditions={config.conditions}
          onChange={(conditions) => update({ conditions })}
          fields={DEDUP_AGG_FIELD_CONFIGS}
          conditionMode={config.condition_mode}
          onConditionModeChange={(mode) => update({ condition_mode: mode })}
        />
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
        <span className="text-sm">保留原始告警</span>
      </label>
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
  group_by: [],
  max_count: 10,
  store_original_alerts: false,
  condition_mode: 'and',
  conditions: [],
}
