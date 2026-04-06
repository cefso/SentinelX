export const OPERATORS = [
  { value: 'eq', label: '等于' },
  { value: 'ne', label: '不等于' },
  { value: 'in', label: '在列表中' },
  { value: 'not_in', label: '不在列表中' },
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'regex', label: '正则匹配' },
  { value: 'gt', label: '大于' },
  { value: 'gte', label: '大于等于' },
  { value: 'lt', label: '小于' },
  { value: 'lte', label: '小于等于' },
  { value: 'exists', label: '存在' },
  { value: 'is_empty', label: '为空' },
]

export const SEVERITY_OPTIONS = ['critical', 'high', 'medium', 'low', 'info']

// 需要从 API 加载值的字段
export const FIELDS_NEED_VALUES = ['namespace', 'instance_id', 'instance_name', 'metric_name', 'alert_key']
