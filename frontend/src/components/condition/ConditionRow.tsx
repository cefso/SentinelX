import { Condition } from '@/pages/rules'
import { OPERATORS, SEVERITY_OPTIONS, FIELDS_NEED_VALUES } from '@/components/condition/constants'

interface ConditionRowProps {
  condition: Condition
  onChange: (field: string, value: any) => void
  onRemove: () => void
  availableFields: { value: string; label: string }[]
  operators?: { value: string; label: string }[]
  showLabelsDropdown?: boolean
  labelsKey?: string
  labelsValueOptions?: { value: string; count: number }[]
  labelsKeyOptions?: string[]
  onLabelsKeyChange?: (key: string) => void
  // 数据源
  sources?: any[]
  fieldValuesCache?: Record<string, { data: { value: string; count: number }[]; timestamp: number }>
  onFetchFieldValues?: (field: string) => void
}

export function ConditionRow({
  condition,
  onChange,
  onRemove,
  availableFields,
  operators = OPERATORS,
  showLabelsDropdown = false,
  labelsKey,
  labelsValueOptions = [],
  labelsKeyOptions = [],
  onLabelsKeyChange,
  sources = [],
  fieldValuesCache = {},
  onFetchFieldValues,
}: ConditionRowProps) {
  const isLabelsField = condition.field === 'labels' || condition.field.startsWith('labels.')
  const isSourceField = condition.field === 'source'
  const isSeverityField = condition.field === 'severity'
  const needsFieldValues = FIELDS_NEED_VALUES.includes(condition.field)

  const getFieldValues = () => {
    if (!fieldValuesCache[condition.field]) return []
    return fieldValuesCache[condition.field].data || []
  }

  const renderValueInput = () => {
    if (['exists', 'is_empty'].includes(condition.operator)) {
      return <span className="text-gray-400 text-sm flex-1 px-2 py-1">无需输入值</span>
    }

    // Labels dropdown mode (for dedup/agg with smart filtering)
    if (showLabelsDropdown && isLabelsField) {
      return (
        <div className="relative flex-1 flex gap-1 items-center">
          {/* Key 下拉框 */}
          <select
            value={labelsKey || ''}
            onChange={(e) => onLabelsKeyChange?.(e.target.value)}
            className="px-2 py-1 border rounded text-sm w-28"
          >
            <option value="">选择标签键</option>
            {labelsKeyOptions.map((key) => (
              <option key={key} value={key}>{key}</option>
            ))}
          </select>

          {/* Value 下拉框 */}
          <select
            value={condition.value}
            onChange={(e) => onChange('value', e.target.value)}
            disabled={!labelsKey}
            className="px-2 py-1 border rounded text-sm flex-1"
          >
            <option value="">选择标签值</option>
            {labelsValueOptions.map((item) => (
              <option key={item.value} value={item.value}>{item.value} ({item.count})</option>
            ))}
          </select>
        </div>
      )
    }

    // in/not_in operators with array values
    if (['in', 'not_in'].includes(condition.operator)) {
      // severity - checkbox list
      if (isSeverityField) {
        return (
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
                        onChange('value', current.filter((v: string) => v !== s))
                      } else {
                        onChange('value', [...current, s])
                      }
                    }}
                    className="w-4 h-4"
                  />
                  <span className="text-sm">{s.toUpperCase()}</span>
                </label>
              )
            })}
          </div>
        )
      }

      // source - checkbox list from API
      if (isSourceField) {
        return (
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
                        onChange('value', current.filter((v: string) => v !== s.source_type))
                      } else {
                        onChange('value', [...current, s.source_type])
                      }
                    }}
                    className="w-4 h-4"
                  />
                  <span className="text-sm">{s.name}</span>
                </label>
              )
            })}
          </div>
        )
      }

      // namespace/instance_id/metric_name/alert_key - checkbox list from cached values
      if (needsFieldValues) {
        const values = getFieldValues()
        if (values.length === 0) {
          return <span className="text-gray-400 text-sm flex-1 px-2 py-1">加载中...</span>
        }
        return (
          <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
            {values.map((item) => {
              const checked = Array.isArray(condition.value) ? condition.value.includes(item.value) : condition.value === item.value
              return (
                <label key={item.value} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      const current = Array.isArray(condition.value) ? condition.value : []
                      if (checked) {
                        onChange('value', current.filter((v: string) => v !== item.value))
                      } else {
                        onChange('value', [...current, item.value])
                      }
                    }}
                    className="w-4 h-4"
                  />
                  <span className="text-sm">{item.value}</span>
                </label>
              )
            })}
          </div>
        )
      }

      // Default text input for other fields
      return (
        <input
          type="text"
          value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
          onChange={(e) => onChange('value', e.target.value)}
          placeholder="多个值用逗号分隔"
          className="px-2 py-1 border rounded text-sm flex-1"
        />
      )
    }

    // eq/ne operators
    if (['eq', 'ne'].includes(condition.operator)) {
      // severity - select dropdown
      if (isSeverityField) {
        return (
          <select
            value={Array.isArray(condition.value) ? condition.value[0] : condition.value}
            onChange={(e) => onChange('value', e.target.value)}
            className="px-2 py-1 border rounded text-sm flex-1"
          >
            <option value="">全部</option>
            {SEVERITY_OPTIONS.map((s) => (
              <option key={s} value={s}>{s.toUpperCase()}</option>
            ))}
          </select>
        )
      }

      // source - select dropdown from API
      if (isSourceField) {
        return (
          <select
            value={Array.isArray(condition.value) ? condition.value[0] : condition.value}
            onChange={(e) => onChange('value', e.target.value)}
            className="px-2 py-1 border rounded text-sm flex-1"
          >
            <option value="">全部</option>
            {sources.map((s: any) => (
              <option key={s.id} value={s.source_type}>{s.name}</option>
            ))}
          </select>
        )
      }

      // namespace/instance_id/metric_name/alert_key - select dropdown from cached values
      if (needsFieldValues) {
        const values = getFieldValues()
        if (values.length === 0) {
          return <span className="text-gray-400 text-sm flex-1 px-2 py-1">加载中...</span>
        }
        return (
          <select
            value={Array.isArray(condition.value) ? condition.value[0] : condition.value}
            onChange={(e) => onChange('value', e.target.value)}
            className="px-2 py-1 border rounded text-sm flex-1"
          >
            <option value="">全部</option>
            {values.map((item) => (
              <option key={item.value} value={item.value}>{item.value} ({item.count})</option>
            ))}
          </select>
        )
      }

      // Labels with dropdown
      if (isLabelsField) {
        return (
          <div className="relative flex-1 flex gap-1 items-center">
            {/* Key 下拉框 */}
            <select
              value={labelsKey || ''}
              onChange={(e) => onLabelsKeyChange?.(e.target.value)}
              className="px-2 py-1 border rounded text-sm w-28"
            >
              <option value="">选择标签键</option>
              {(labelsKeyOptions || []).map((key: string) => (
                <option key={key} value={key}>{key}</option>
              ))}
            </select>

            {/* Value 下拉框 */}
            <select
              value={condition.value}
              onChange={(e) => onChange('value', e.target.value)}
              disabled={!labelsKey}
              className="px-2 py-1 border rounded text-sm flex-1"
            >
              <option value="">选择标签值</option>
              {labelsKey && labelsValueOptions.map((item) => (
                <option key={item.value} value={item.value}>{item.value} ({item.count})</option>
              ))}
            </select>
          </div>
        )
      }

      // Default text input
      return (
        <input
          type="text"
          value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
          onChange={(e) => onChange('value', e.target.value)}
          placeholder="输入值"
          className="px-2 py-1 border rounded text-sm flex-1"
        />
      )
    }

    // Default text input for other operators
    return (
      <input
        type="text"
        value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
        onChange={(e) => onChange('value', e.target.value)}
        placeholder="输入值"
        className="px-2 py-1 border rounded text-sm flex-1"
      />
    )
  }

  return (
    <div className="flex gap-2 items-center">
      <select
        value={condition.field}
        onChange={(e) => {
          const newField = e.target.value
          // If changing from labels.xxx to non-labels, reset key
          if (condition.field.startsWith('labels.') && !newField.startsWith('labels.')) {
            onChange('field', newField)
            onChange('key', '')
          } else {
            onChange('field', newField)
          }
          // Fetch field values for new field if needed
          if (onFetchFieldValues && FIELDS_NEED_VALUES.includes(newField)) {
            onFetchFieldValues(newField)
          }
        }}
        className="px-2 py-1 border rounded text-sm"
      >
        {availableFields.map((f) => (
          <option key={f.value} value={f.value}>{f.label}</option>
        ))}
      </select>

      <select
        value={condition.operator}
        onChange={(e) => onChange('operator', e.target.value)}
        className="px-2 py-1 border rounded text-sm"
      >
        {operators.map((op) => (
          <option key={op.value} value={op.value}>{op.label}</option>
        ))}
      </select>

      {renderValueInput()}

      <button
        type="button"
        onClick={onRemove}
        className="text-red-600 hover:text-red-800"
      >
        ×
      </button>
    </div>
  )
}
