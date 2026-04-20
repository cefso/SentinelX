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

export const STATUS_OPTIONS = [
  { value: 'firing', label: '触发中' },
  { value: 'resolved', label: '已恢复' },
  { value: 'suppressed', label: '已抑制' },
  { value: 'acknowledged', label: '已确认' },
]

// 需要从 API 加载值的字段
export const FIELDS_NEED_VALUES = ['namespace', 'instance_id', 'instance_name', 'metric_name', 'alert_key']

// ============ 统一字段配置 ============

export type FieldType = 'enum' | 'string' | 'number' | 'labels'
export type ValueSource = 'fixed' | 'api' | 'free' | 'labels'

export interface FieldConfig {
  value: string
  label: string
  type: FieldType
  operators: string[]
  valueSource: ValueSource
  fixedValues?: string[]
  fixedLabels?: Record<string, string>  // value -> display label
  apiField?: string  // 用于 API 查询的字段名
}

const ENUM_OPERATORS = ['eq', 'ne', 'in', 'not_in', 'exists', 'is_empty']
const STRING_OPERATORS = ['eq', 'ne', 'contains', 'not_contains', 'regex', 'exists', 'is_empty']
const NUMBER_OPERATORS = ['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'exists', 'is_empty']

export const FIELD_CONFIGS: FieldConfig[] = [
  {
    value: 'severity',
    label: '严重级别',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'fixed',
    fixedValues: SEVERITY_OPTIONS,
  },
  {
    value: 'status',
    label: '状态',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'fixed',
    fixedValues: STATUS_OPTIONS.map(s => s.value),
    fixedLabels: Object.fromEntries(STATUS_OPTIONS.map(s => [s.value, s.label])),
  },
  {
    value: 'source_id',
    label: '告警来源',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'source',
  },
  {
    value: 'namespace',
    label: '命名空间',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'namespace',
  },
  {
    value: 'instance_id',
    label: '实例ID',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'instance_id',
  },
  {
    value: 'instance_name',
    label: '实例名称',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'instance_name',
  },
  {
    value: 'metric_name',
    label: '指标',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'metric_name',
  },
  {
    value: 'alert_key',
    label: '告警Key',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'alert_key',
  },
  {
    value: 'assignee',
    label: '处理人',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'assignee',
  },
  {
    value: 'title',
    label: '标题',
    type: 'string',
    operators: STRING_OPERATORS,
    valueSource: 'free',
  },
  {
    value: 'content',
    label: '内容',
    type: 'string',
    operators: STRING_OPERATORS,
    valueSource: 'free',
  },
  {
    value: 'fire_count',
    label: '触发次数',
    type: 'number',
    operators: NUMBER_OPERATORS,
    valueSource: 'free',
  },
  {
    value: 'repeat_count',
    label: '重复次数',
    type: 'number',
    operators: NUMBER_OPERATORS,
    valueSource: 'free',
  },
  {
    value: 'escalation_count',
    label: '升级次数',
    type: 'number',
    operators: NUMBER_OPERATORS,
    valueSource: 'free',
  },
  {
    value: 'labels',
    label: '标签',
    type: 'labels',
    operators: ENUM_OPERATORS,
    valueSource: 'labels',
  },
]

// 去重/聚合可用字段（排除 labels，labels 单独处理）
export const DEDUP_AGG_FIELD_CONFIGS: FieldConfig[] = [
  {
    value: 'alert_key',
    label: '告警Key',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'alert_key',
  },
  {
    value: 'source',
    label: '告警来源',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'source',
  },
  {
    value: 'severity',
    label: '严重级别',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'fixed',
    fixedValues: SEVERITY_OPTIONS,
  },
  {
    value: 'namespace',
    label: '命名空间',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'namespace',
  },
  {
    value: 'instance_id',
    label: '实例ID',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'instance_id',
  },
  {
    value: 'metric_name',
    label: '指标',
    type: 'enum',
    operators: ENUM_OPERATORS,
    valueSource: 'api',
    apiField: 'metric_name',
  },
  {
    value: 'title',
    label: '标题',
    type: 'string',
    operators: STRING_OPERATORS,
    valueSource: 'free',
  },
  {
    value: 'content',
    label: '内容',
    type: 'string',
    operators: STRING_OPERATORS,
    valueSource: 'free',
  },
  {
    value: 'labels',
    label: '标签',
    type: 'labels',
    operators: ENUM_OPERATORS,
    valueSource: 'labels',
  },
]
