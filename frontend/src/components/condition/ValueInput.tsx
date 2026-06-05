import { useState, useRef, useEffect } from 'react'
import type { Condition } from './ConditionEditor'
import type { FieldConfig } from './constants'

interface ValueInputProps {
  condition: Condition
  index: number
  config: FieldConfig | undefined
  showLabelsDropdown: boolean
  labelsKeyOptions: string[]
  labelsValueOptionsByKey: Record<string, { value: string; count: number }[]>
  fieldValuesCache: React.MutableRefObject<Record<string, { data: { value: string; count: number }[]; timestamp: number; error?: boolean }>>
  sources: any[]
  users: any[]
  updateCondition: (index: number, key: string, value: any) => void
  fetchFieldValues: (field: string) => void
}

export function ValueInput({
  condition,
  index,
  config,
  showLabelsDropdown,
  labelsKeyOptions,
  labelsValueOptionsByKey,
  fieldValuesCache,
  sources,
  users,
  updateCondition,
  fetchFieldValues,
}: ValueInputProps) {
  const [localLabelsKey, setLocalLabelsKey] = useState<string>('')
  const [openFieldKey, setOpenFieldKey] = useState<string>('')
  const dropdownRef = useRef<HTMLDivElement | null>(null)

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

  const toggleFieldValuesDropdown = (field: string) => {
    const key = `${index}-${field}`
    if (openFieldKey === key) {
      setOpenFieldKey('')
    } else {
      setOpenFieldKey(key)
      if (config?.apiField) fetchFieldValues(config.apiField)
    }
  }

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
    const labelsKey = localLabelsKey || condition.key || ''
    const labelsCached = fieldValuesCache.current['labels']
    const labelValuesCached = labelsKey ? fieldValuesCache.current[`labels.${labelsKey}`] : null
    const isInOperator = ['in', 'not_in'].includes(condition.operator)

    return (
      <div className="relative flex-1 flex gap-1 items-center">
        <select
          value={labelsKey}
          onChange={(e) => {
            const key = e.target.value
            setLocalLabelsKey(key)
            updateCondition(index, 'key', key)
            updateCondition(index, 'field', key ? `labels.${key}` : 'labels')
            updateCondition(index, 'value', isInOperator ? [] : '')
            if (key) fetchFieldValues(`labels.${key}`)
          }}
          className="px-2 py-1 border rounded text-sm w-28"
        >
          <option value="">选择标签键</option>
          {(labelsCached?.data || []).map((item: any) => (
            <option key={item.value} value={item.value}>{item.value}</option>
          ))}
        </select>
        {isInOperator ? (
          <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
            {(labelValuesCached?.data?.length ?? 0) > 0 ? (
              labelValuesCached!.data.map((item: any) => {
                const checked = Array.isArray(condition.value) ? condition.value.includes(item.value) : false
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
                    <span className="text-sm">{item.value} ({item.count})</span>
                  </label>
                )
              })
            ) : (
              <span className="text-gray-400 text-sm">无可选值</span>
            )}
          </div>
        ) : (
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
        )}
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

    // Source from API（source_id 字段，值存为数字以匹配告警数据）
    if (config?.apiField === 'source') {
      return (
        <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
          {sources.map((s: any) => {
            const checked = Array.isArray(condition.value)
              ? condition.value.some((v) => Number(v) === s.id)
              : Number(condition.value) === s.id
            return (
              <label key={s.id} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => {
                    const current = Array.isArray(condition.value) ? condition.value : []
                    if (checked) {
                      updateCondition(index, 'value', current.filter((v) => Number(v) !== s.id))
                    } else {
                      updateCondition(index, 'value', [...current, s.id])
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

    // Assignee from API（值存为数字以匹配告警数据）
    if (config?.apiField === 'assignee') {
      return (
        <div className="flex-1 border rounded px-2 py-1 space-y-1 max-h-32 overflow-y-auto">
          {users.map((u: any) => {
            const checked = Array.isArray(condition.value)
              ? condition.value.some((v) => Number(v) === u.id)
              : Number(condition.value) === u.id
            return (
              <label key={u.id} className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => {
                    const current = Array.isArray(condition.value) ? condition.value : []
                    if (checked) {
                      updateCondition(index, 'value', current.filter((v) => Number(v) !== u.id))
                    } else {
                      updateCondition(index, 'value', [...current, u.id])
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
      if (!cached) {
        return <span className="text-gray-400 text-sm flex-1 px-2 py-1">加载中...</span>
      }
      if (cached.data.length === 0) {
        return (
          <input
            type="text"
            value={Array.isArray(condition.value) ? condition.value.join(',') : condition.value}
            onChange={(e) => updateCondition(index, 'value', e.target.value)}
            placeholder="输入值，多个值用逗号分隔"
            className="px-2 py-1 border rounded text-sm flex-1"
          />
        )
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
      const selected = Array.isArray(condition.value) ? condition.value[0] : condition.value
      return (
        <select
          value={selected ?? ''}
          onChange={(e) => {
            const raw = e.target.value
            updateCondition(index, 'value', raw === '' ? '' : Number(raw))
          }}
          className="px-2 py-1 border rounded text-sm flex-1"
        >
          <option value="">全部</option>
          {sources.map((s: any) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
      )
    }

    // Assignee from API
    if (config?.apiField === 'assignee') {
      const selected = Array.isArray(condition.value) ? condition.value[0] : condition.value
      return (
        <select
          value={selected ?? ''}
          onChange={(e) => {
            const raw = e.target.value
            updateCondition(index, 'value', raw === '' ? '' : Number(raw))
          }}
          className="px-2 py-1 border rounded text-sm flex-1"
        >
          <option value="">全部</option>
          {users.map((u: any) => (
            <option key={u.id} value={u.id}>{u.username}</option>
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
            onClick={() => toggleFieldValuesDropdown(condition.field)}
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
          onClick={() => toggleFieldValuesDropdown(condition.field)}
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
