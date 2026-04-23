import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import {
  OPERATORS,
  FieldConfig,
} from '@/components/condition/constants'
import { ValueInput } from './ValueInput'

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
  const [loadedFieldKeys, setLoadedFieldKeys] = useState<Set<string>>(new Set())
  const fieldValuesCache = useRef<Record<string, { data: { value: string; count: number }[]; timestamp: number; error?: boolean }>>({})

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

  // 预加载 labels 字段的 key 列表（valueSource 为 'labels'，不在 apiFields 预加载范围内）
  useEffect(() => {
    if (fields.some(f => f.valueSource === 'labels')) {
      fetchFieldValues('labels')
    }
  }, [])

  // 预填充条件中可能已有 labels.{key}，需要预加载其值
  useEffect(() => {
    conditions.forEach(cond => {
      if (cond.field && cond.field.startsWith('labels.')) {
        fetchFieldValues(cond.field)
      }
    })
  }, [])

  const fetchFieldValues = async (field: string) => {
    const now = Date.now()
    const cached = fieldValuesCache.current[field]
    if (cached && now - cached.timestamp < 60000) {
      if (!loadedFieldKeys.has(field)) {
        setLoadedFieldKeys(prev => new Set([...prev, field]))
      }
      return
    }
    try {
      const result = await apiClient.getRuleFieldValues({ field, limit: 50 })
      fieldValuesCache.current[field] = { data: result.values, timestamp: now }
      setLoadedFieldKeys(prev => new Set([...prev, field]))
    } catch (err) {
      console.error('Failed to fetch field values:', err)
      fieldValuesCache.current[field] = { data: [], timestamp: now, error: true }
    }
  }

  const getFieldConfig = (fieldValue: string): FieldConfig | undefined => {
    return fields.find(f => f.value === fieldValue)
      || (fieldValue.startsWith('labels.') ? fields.find(f => f.value === 'labels') : undefined)
  }

  const getOperatorsForField = (fieldValue: string) => {
    const config = getFieldConfig(fieldValue)
    if (!config) return OPERATORS
    return OPERATORS.filter(op => config.operators.includes(op.value))
  }

  const addCondition = useCallback(() => {
    const defaultField = fields[0]?.value || 'severity'
    onChange([...conditions, { field: defaultField, operator: 'in', value: [] }])
  }, [conditions, onChange, fields])

  const removeCondition = useCallback((index: number) => {
    onChange(conditions.filter((_, i) => i !== index))
  }, [conditions, onChange])

  const updateCondition = useCallback((index: number, key: string, value: any) => {
    const newConditions = [...conditions]
    newConditions[index] = { ...newConditions[index], [key]: value }
    onChange(newConditions)
  }, [conditions, onChange])

  const handleFieldChange = useCallback((index: number, newField: string) => {
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
  }, [conditions, onChange])

  const handleOperatorChange = useCallback((index: number, newOperator: string) => {
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

    // 一次性更新 operator 和 value，避免 React 18 批量处理导致 operator 更新丢失
    const newConditions = [...conditions]
    newConditions[index] = { ...newConditions[index], operator: newOperator, value: newValue }
    onChange(newConditions)
  }, [conditions, onChange])

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

            <ValueInput
              condition={condition}
              index={index}
              config={getFieldConfig(condition.field)}
              showLabelsDropdown={showLabelsDropdown}
              labelsKeyOptions={labelsKeyOptions}
              labelsValueOptionsByKey={labelsValueOptionsByKey}
              fieldValuesCache={fieldValuesCache}
              sources={sources}
              users={users}
              updateCondition={updateCondition}
              fetchFieldValues={fetchFieldValues}
            />

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
