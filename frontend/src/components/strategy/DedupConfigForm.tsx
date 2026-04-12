import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { DEDUP_AGG_FIELD_CONFIGS } from '@/components/condition/constants'

export interface DedupConfig {
  enabled: boolean
  mode: 'fingerprint' | 'condition'
  fingerprint_fields: string[]
  window_seconds: number
  dimensions: { by_severity: boolean; by_source: boolean }
  strategy: 'first' | 'last'
  condition_mode: string
  conditions: Condition[]
}

interface DedupConfigFormProps {
  config: DedupConfig
  onChange: (config: DedupConfig) => void
}

export function DedupConfigForm({ config, onChange }: DedupConfigFormProps) {
  const update = (partial: Partial<DedupConfig>) => {
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
            name="dedup-mode"
            checked={config.mode === 'fingerprint'}
            onChange={() => update({ mode: 'fingerprint' })}
          />
          <span className="text-sm">指纹模式</span>
        </label>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="dedup-mode"
            checked={config.mode === 'condition'}
            onChange={() => update({ mode: 'condition' })}
          />
          <span className="text-sm">条件模式</span>
        </label>
      </div>

      {config.mode === 'fingerprint' && (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600 w-20">指纹字段:</span>
            {['alert_key', 'source', 'namespace', 'severity', 'instance_id', 'metric_name'].map((field) => (
              <label key={field} className="flex items-center gap-1">
                <input
                  type="checkbox"
                  checked={config.fingerprint_fields.includes(field)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      update({ fingerprint_fields: [...config.fingerprint_fields, field] })
                    } else {
                      update({ fingerprint_fields: config.fingerprint_fields.filter(f => f !== field) })
                    }
                  }}
                />
                <span className="text-sm">{field}</span>
              </label>
            ))}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-600 w-20">维度细分:</span>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={config.dimensions.by_severity}
                onChange={(e) => update({ dimensions: { ...config.dimensions, by_severity: e.target.checked } })}
              />
              <span className="text-sm">按 severity</span>
            </label>
            <label className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={config.dimensions.by_source}
                onChange={(e) => update({ dimensions: { ...config.dimensions, by_source: e.target.checked } })}
              />
              <span className="text-sm">按 source</span>
            </label>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 w-20">策略:</span>
            <label className="flex items-center gap-1">
              <input
                type="radio"
                name="dedup-strategy"
                checked={config.strategy === 'first'}
                onChange={() => update({ strategy: 'first' })}
              />
              <span className="text-sm">首次</span>
            </label>
            <label className="flex items-center gap-1">
              <input
                type="radio"
                name="dedup-strategy"
                checked={config.strategy === 'last'}
                onChange={() => update({ strategy: 'last' })}
              />
              <span className="text-sm">最后</span>
            </label>
          </div>
        </>
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
    </div>
  )
}

export function dedupConfigToPayload(config: DedupConfig): any {
  const payload: any = {
    enabled: true,
    dedup_type: config.mode,
    window_seconds: config.window_seconds,
  }
  if (config.mode === 'fingerprint') {
    payload.fingerprint_fields = config.fingerprint_fields
    payload.dimensions = config.dimensions
    payload.strategy = config.strategy
  } else {
    payload.conditions = config.conditions
    payload.condition_mode = config.condition_mode
  }
  return payload
}

export const DEFAULT_DEDUP_CONFIG: DedupConfig = {
  enabled: true,
  mode: 'fingerprint',
  fingerprint_fields: ['alert_key'],
  window_seconds: 300,
  dimensions: { by_severity: false, by_source: false },
  strategy: 'first',
  condition_mode: 'and',
  conditions: [],
}
