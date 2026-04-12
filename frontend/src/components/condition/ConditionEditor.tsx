import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import {
  OPERATORS,
  FieldConfig,
} from '@/components/condition/constants'

export interface Condition {
  field: string
  operator: string
  value: any
  key?: string  // 用于 labels 字段的 key 传递
}

interface ConditionEditorProps {
  conditions: Condition[]
  onChange: (conditions: Condition[]) => void
  fields: FieldConfig[]
  conditionMode?: string
  onConditionModeChange?: (mode: string) => void
  // 去重/聚合 labels 支持
  showLabelsDropdown?: boolean
  labelsKeyOptions?: string[]
  labelsValueOptionsByKey?: Record<string, { value: string; count: number }[]>
}

export function ConditionEditor({
  conditions,
  onChange,
  fields,
  conditionMode,
  onConditionModeChange,
  showLabelsDropdown = false,
  labelsKeyOptions = [],
  labelsValueOptionsByKey = {},
}: ConditionEditorProps) {
  const [openFieldKey, setOpenFieldKey] = useState<string>('')
  const dropdownRef = useRef<HTMLDivElement | null>(null)
  const fieldValuesCache = useRef<Record<string, { data: { value: string; count: number }[]; timestamp: number }>>({})

  // 获取需要 API 数据的字段
  const apiFields = fields.filter(f => f.valueSource === 'api')

  // 加载数据源
  const { data: sources = [] } = useQuery<any[]>({
    queryKey: ['alert-sources'],
    queryFn: () => apiClient.get('/sources'),
    enabled: apiFields.some(f => f.apiField === 'source'),
  })

  const { data: users = [] } = useQuery<any[]>({
    queryKey: ['users'],
    queryFn: () => apiClient.get('/users'),
    enabled: apiFields.some(f => f.apiField === 'assignee'),
  })

  // 预加载 API 字段值
  useEffect(() => {
    apiFields.forEach(f => {
      if (f.apiField && f.apiField !== 'source' && f.apiField !== 'assignee') {
        fetchFieldValues(f.apiField)
      }
    })
  }, [])

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
    if (cached && now - cached.timestamp < 60000) return
    try {
      const result = await apiClient.getRuleFieldValues({ field, limit: 50 })
      fieldValuesCache.current[field] = { data: result.values, timestamp: now }
    } catch (err) {
      console.error('Failed to fetch field values:', err)
    }
  }

  const getFieldConfig = (fieldValue: string): FieldConfig | undefined => {
    return fields.find(f => f.value === fieldValue)
  }

  const getOperatorsForField = (fieldValue: string) => {
    const config = getFieldConfig(fieldValue)
    if (!config) return OPERATORS
    return OPERATORS.filter(op => config.operators.includes(op.value))
  }

  const addCondition = () => {
    const defaultField = fields[0]?.value || 'severity'
    onChange([...conditions, { field: defaultField, operator: 'in', value: [] }])
  }

  const removeCondition = (index: number) => {
    onChange(conditions.filter((_, i) => i !== index))
  }

  const updateCondition = (index: number, key: string, value: any) => {
    const newConditions = [...conditions]
    newConditions[index] = { ...newConditions[index], [key]: value }
    onChange(newConditions)
  }

  const handleFieldChange = (index: number, newField: string) => {
    const oldCond = conditions[index]
    const newCond: Condition = { field: newField, operator: oldCond.operator, value: '' }

    // 保留 labels key
    if (oldCond.field.startsWith('labels.') && newField.startsWith('labels.')) {
      newCond.key = oldCond.key
    }

    // 如果新字段的运算符不在可用列表中，重置为第一个可用运算符
    const config = getFieldConfig(newField)
    if (config && !config.operators.includes(oldCond.operator)) {
      newCond.operator = config.operators[0] || 'eq'
    }

    const newConditions = [...conditions]
    newConditions[index] = newCond
    onChange(newConditions)

    // 预加载 API 字段值
    const fc = getFieldConfig(newField)
    if (fc?.valueSource === 'api' && fc.apiField) {
      fetchFieldValues(fc.apiField)
    }
  }

  const handleOperatorChange = (index: number, newOperator: string) => {
    const cond = conditions[index]
    let newValue: any = ''

    if (['in', 'not_in'].includes(newOperator)) {
      if (typeof cond.value === 'string' && cond.value) {
        newValue = cond.value.split(',').map((v: string) => v.trim()).filter((v: string) => v)
      } else if (Array.isArray(cond.value)) {
        newValue = cond.value
      } else {
        newValue = []
      }
    } else if (['exists', 'is_empty'].includes(newOperator)) {
      newValue = ''
    } else {
      if (Array.isArray(cond.value) && cond.value.length > 0) {
        newValue = cond.value[0] || ''
      } else if (Array.isArray(cond.value)) {
        newValue = ''
      } else {
        newValue = cond.value || ''
      }
    }

    updateCondition(index, 'operator', newOperator)
    updateCondition(index, 'value', newValue)
  }

  const toggleFieldValuesDropdown = (index: number, field: string) => {
    const key = `${index}-${field}`
    if (openFieldKey === key) {
      setOpenFieldKey('')
    } else {
      setOpenFieldKey(key)
      const fc = getFieldConfig(field)
      if (fc?.apiField) fetchFieldValues(fc.apiField)
    }
  }

  const renderValueInput = (condition: Condition, index: number) => {
    const config = getFieldConfig(condition.field)

    if (['exists', 'is_empty'].includes(condition.operator)) {
      return <span className="text-gray-400 text-sm flex-1 px-2 py-1">无需输入值</span>
    }

    // Labels with dropdown mode (for dedup/agg)
    if (showLabelsDropdown && config?.valueSource === 'labels') {
      const labelsKey = condition.key || ''
      const valueOptions = labelsValueOptionsByKey[labelsKey] || []
      return (
        <div className="relative flex-1 flex gap-1 items-center">
          <select
            value={labelsKey}
            onChange={(e) => {
              const key = e.target.value
              updateCondition(index, 'key', key)
              updateCondition(index, 'field', key ? `labels.${key}` : 'labels')
              updateCondition(index, 'value', '')
            }}
            className="px-2 py-1 border rounded text-sm w-28"
          >
            <option value="">选择标签键</option>
            {labelsKeyOptions.map((k) => (
              <option key={k} value={k}>{k}</option>
            ))}
          </select>
          <select
            value={condition.value}
            onChange={(e) => updateCondition(index, 'value', e.target.value)}
            disabled={!labelsKey}
            className="px-2 py-1 border rounded text-sm flex-1"
          >
            <option value="">选择标签值</option>
            {valueOptions.map((item) => (
              <option key={item.value} value={item.value}>{item.value} ({item.count})</option>
            ))}
          </select>
        </div>
      )
    }

    // Labels with key+value dropdown (main rule)
    if (config?.valueSource === 'labels' && !showLabelsDropdown) {
      const labelsKey = condition.key || ''
      const labelsCached = fieldValuesCache.current['labels']
      const labelValuesCached = labelsKey ? fieldValuesCache.current[`labels.${labelsKey}`] : null

      return (
        <div className="relative flex-1 flex gap-1 items-center">
          <select
            value={labelsKey}
            onChange={(e) => {
              const key = e.target.value
              updateCondition(index, 'key', key)
              updateCondition(index, 'field', key ? `labels.${key}` : 'labels')
              updateCondition(index, 'value', '')
              if (key) fetchFieldValues(`labels.${key}`)
            }}
            className="px-2 py-1 border rounded text-sm w-28"
          >
            <option value="">选择标签键</option>
            {(labelsCached?.data || []).map((item: any) => (
              <option key={item.value} value={item.value}>{item.value}</option>
            ))}
          </select>
          <select
            value={condition.value}
            onChange={(e) => updateCondition(index, 'value', e.target.value)}
            disabled={!labelsKey}
            className="px-2 py-1 border rounded text-sm flex-1"
          >
            <option value="">选择标签值</option>
            {(labelValuesCached?.data || []).map((item: any) => (
              <option key={item.value} value={item.value}>{item.value} ({item.count})</option>
            ))}
          </select>
        </div>
      )
    }

    // in/not_in operators
    if (['in', 'not_in'].includes(condition.operator)) {
      // Fixed values (severity, status)
      if (config?.valueSource === 'fixed' && config.fixedValues) {
        return (
          <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
            {config.fixedValues.map((v) => {
              const checked = Array.isArray(condition.value) ? condition.value.includes(v) : condition.value === v
              const displayLabel = config.fixedLabels?.[v] || v.toUpperCase()
              return (
                <label key={v} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => {
                      const current = Array.isArray(condition.value) ? condition.value : []
                      if (checked) {
                        updateCondition(index, 'value', current.filter((val: string) => val !== v))
                      } else {
                        updateCondition(index, 'value', [...current, v])
                      }
                    }}
                    className="w-4 h-4"
                  />
                  <span className="text-sm">{displayLabel}</span>
                </label>
              )
            })}
          </div>
        )
      }

      // Source from API
      if (config?.apiField === 'source') {
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
        )
      }

      // Assignee from API
      if (config?.apiField === 'assignee') {
        return (
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
        )
      }

      // API fields (namespace, instance_id, metric_name, alert_key)
      if (config?.valueSource === 'api' && config.apiField) {
        const cached = fieldValuesCache.current[config.apiField]
        if (!cached || cached.data.length === 0) {
          return <span className="text-gray-400 text-sm flex-1 px-2 py-1">加载中...</span>
        }
        return (
          <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
            {cached.data.map((item) => {
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
            })}
          </div>
        )
      }

      // Default text input for in/not_in
      return (
        <input
          type="text"
          value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
          onChange={(e) => updateCondition(index, 'value', e.target.value)}
          placeholder="多个值用逗号分隔"
          className="px-2 py-1 border rounded text-sm flex-1"
        />
      )
    }

    // eq/ne operators
    if (['eq', 'ne'].includes(condition.operator)) {
      // Fixed values (severity, status)
      if (config?.valueSource === 'fixed' && config.fixedValues) {
        return (
          <select
            value={Array.isArray(condition.value) ? condition.value[0] : condition.value}
            onChange={(e) => updateCondition(index, 'value', e.target.value)}
            className="px-2 py-1 border rounded text-sm flex-1"
          >
            <option value="">全部</option>
            {config.fixedValues.map((v) => {
              const displayLabel = config.fixedLabels?.[v] || v.toUpperCase()
              return <option key={v} value={v}>{displayLabel}</option>
            })}
          </select>
        )
      }

      // Source from API
      if (config?.apiField === 'source') {
        return (
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
        )
      }

      // Assignee from API
      if (config?.apiField === 'assignee') {
        return (
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
        )
      }

      // API fields with dropdown
      if (config?.valueSource === 'api' && config.apiField) {
        const cached = fieldValuesCache.current[config.apiField]
        return (
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
                {!cached || cached.data.length === 0 ? (
                  <div className="px-3 py-2 text-sm text-gray-500">
                    {!cached ? '加载中...' : '无可选值'}
                  </div>
                ) : (
                  cached.data.map((item) => (
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
        )
      }
    }

    // Default: text input (for other operators or free-text fields)
    if (config?.valueSource === 'api' && config.apiField) {
      const cached = fieldValuesCache.current[config.apiField]
      return (
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
              {!cached || cached.data.length === 0 ? (
                <div className="px-3 py-2 text-sm text-gray-500">
                  {!cached ? '加载中...' : '无可选值'}
                </div>
              ) : (
                cached.data.map((item) => (
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
      )
    }

    return (
      <input
        type="text"
        value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
        onChange={(e) => updateCondition(index, 'value', e.target.value)}
        placeholder="输入值"
        className="px-2 py-1 border rounded text-sm flex-1"
      />
    )
  }

  return (
    <div>
      {conditionMode && onConditionModeChange && (
        <div className="flex items-center gap-2 mb-2">
          <span className="text-sm text-gray-600">组合方式:</span>
          <select
            value={conditionMode}
            onChange={(e) => onConditionModeChange(e.target.value)}
            className="px-2 py-1 border rounded text-sm"
          >
            <option value="and">AND (全部满足)</option>
            <option value="or">OR (任一满足)</option>
          </select>
        </div>
      )}
      <div className="space-y-2">
        {conditions.map((condition, index) => (
          <div key={index} className="flex gap-2 items-center">
            <select
              value={condition.field}
              onChange={(e) => handleFieldChange(index, e.target.value)}
              className="px-2 py-1 border rounded text-sm"
            >
              {fields.map((f) => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>

            <select
              value={condition.operator}
              onChange={(e) => handleOperatorChange(index, e.target.value)}
              className="px-2 py-1 border rounded text-sm"
            >
              {getOperatorsForField(condition.field).map((op) => (
                <option key={op.value} value={op.value}>{op.label}</option>
              ))}
            </select>

            {renderValueInput(condition, index)}

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
      <button
        type="button"
        onClick={addCondition}
        className="mt-2 text-sm text-blue-600 hover:text-blue-800"
      >
        + 添加条件
      </button>
    </div>
  )
}
