import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { FIELD_CONFIGS } from '@/components/condition/constants'

export interface SuppressConfig {
  enabled: boolean
  type: 'maintenance_window' | 'rule_based'
  duration_minutes: number
  cluster_labels: string[]
  rule_conditions: Condition[]
}

interface SuppressConfigFormProps {
  config: SuppressConfig
  onChange: (config: SuppressConfig) => void
}

export function SuppressConfigForm({ config, onChange }: SuppressConfigFormProps) {
  const update = (partial: Partial<SuppressConfig>) => {
    onChange({ ...config, ...partial })
  }

  const suppressFields = FIELD_CONFIGS.filter(f =>
    ['source', 'severity', 'namespace', 'instance_id', 'labels'].includes(f.value)
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-600">类型:</span>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="suppress-type"
            checked={config.type === 'maintenance_window'}
            onChange={() => update({ type: 'maintenance_window' })}
          />
          <span className="text-sm">维护窗口</span>
        </label>
        <label className="flex items-center gap-1">
          <input
            type="radio"
            name="suppress-type"
            checked={config.type === 'rule_based'}
            onChange={() => update({ type: 'rule_based' })}
          />
          <span className="text-sm">规则匹配</span>
        </label>
      </div>

      {config.type === 'maintenance_window' && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">持续时间:</span>
          <input
            type="number"
            value={config.duration_minutes}
            onChange={(e) => update({ duration_minutes: parseInt(e.target.value) || 0 })}
            className="px-2 py-1 border rounded text-sm w-24"
          />
          <span className="text-sm text-gray-500">分钟</span>
        </div>
      )}

      {config.type === 'rule_based' && (
        <ConditionEditor
          conditions={config.rule_conditions}
          onChange={(conditions) => update({ rule_conditions: conditions })}
          fields={suppressFields}
        />
      )}
    </div>
  )
}

export function suppressConfigToPayload(config: SuppressConfig): any {
  const payload: any = {
    enabled: true,
    type: config.type,
  }
  if (config.type === 'maintenance_window') {
    payload.maintenance_window = {
      duration_minutes: config.duration_minutes,
      cluster_labels: config.cluster_labels,
    }
  } else {
    payload.rule_based = {
      conditions: config.rule_conditions,
      delay_seconds: 0,
    }
  }
  return payload
}

export const DEFAULT_SUPPRESS_CONFIG: SuppressConfig = {
  enabled: true,
  type: 'maintenance_window',
  duration_minutes: 60,
  cluster_labels: [],
  rule_conditions: [],
}
