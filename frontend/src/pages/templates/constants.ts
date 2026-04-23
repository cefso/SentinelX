export const CHANNEL_TYPES = [
  { value: 'dingtalk', label: '钉钉' },
  { value: 'feishu', label: '飞书' },
  { value: 'wecom', label: '企业微信' },
  { value: 'email', label: '邮件' },
  { value: 'webhook', label: 'Webhook' },
  { value: 'slack', label: 'Slack' },
]

export const CHANNEL_TYPE_LABELS: Record<string, string> = {
  dingtalk: '钉钉',
  feishu: '飞书',
  wecom: '企业微信',
  email: '邮件',
  webhook: 'Webhook',
  slack: 'Slack',
}

const COMMON_VARIABLES = [
  '{{ alert.title }} - 告警标题',
  '{{ alert.content }} - 告警内容',
  '{{ alert.severity }} - 严重级别 (critical/high/medium/low/info)',
  '{{ alert.status }} - 状态 (firing/resolved)',
  '{{ alert.source }} - 告警来源',
  '{{ alert.fired_at }} - 触发时间',
  '{{ alert.fire_count }} - 触发次数',
  '{{ alert.labels.xxx }} - 标签',
  '{{ alert.namespace }} - 命名空间',
  '{{ alert.instance_name }} - 实例名称',
  '{{ alert.instance_id }} - 实例ID',
  '{{ alert.metric_name }} - 指标名',
  '{{ alert.metric_value }} - 指标值',
  '{{ alert.raw_data.xxx }} - 提取原始告警数据中的任意字段',
  '{{ alert.annotations.xxx }} - 提取注解中的字段',
  '{{ alert.extra_data.xxx }} - 提取扩展数据中的字段',
  '{{ alert.fingerprint }} - 告警指纹',
]

export const VARIABLE_DOCS: Record<string, { label: string; variables: string[] }> = {
  dingtalk: { label: '钉钉可用变量', variables: COMMON_VARIABLES },
  feishu: { label: '飞书可用变量', variables: COMMON_VARIABLES },
  wecom: { label: '企业微信可用变量', variables: COMMON_VARIABLES },
  email: { label: '邮件可用变量', variables: COMMON_VARIABLES },
  webhook: { label: 'Webhook可用变量', variables: COMMON_VARIABLES },
  slack: { label: 'Slack可用变量', variables: COMMON_VARIABLES },
}

export const EXAMPLE_ALERT = {
  id: 1,
  fingerprint: 'abc123def456',
  source: 'prometheus',
  title: '[Critical] CPU使用率过高',
  content: '服务器 CPU 使用率超过 90%，已持续 5 分钟',
  severity: 'critical',
  status: 'firing',
  labels: { env: 'production', region: 'us-east-1', host: 'web-server-01' },
  annotations: { runbook: 'https://wiki.example.com/runbooks/cpu-high' },
  raw_data: { cpu: 95.5, memory: 78.2, disk: 65.0 },
  extra_data: { duration: '5min', threshold: 90 },
  fire_count: 3,
  fired_at: '2026-04-18T10:30:00Z',
  namespace: 'ecs',
  instance_name: 'web-server-01',
  instance_id: 'i-xxxxx',
  metric_name: 'cpu_usage',
  metric_value: 95.5,
}

export function renderJinja2Preview(template: string, alert: Record<string, any>): string {
  let result = template

  result = result.replace(/\{\{\s*alert\.(\w+)\s*\}\}/g, (_, key) => {
    return alert[key] !== undefined ? String(alert[key]) : `{{ alert.${key} }}`
  })

  result = result.replace(/\{\{\s*alert\.(\w+)\.(\w+)\s*\}\}/g, (_, section, key) => {
    const sectionData = alert[section]
    if (sectionData && typeof sectionData === 'object' && key in sectionData) {
      return String(sectionData[key])
    }
    return `{{ alert.${section}.${key} }}`
  })

  const ifRegex = /\{%\s*if\s+alert\.(\w+)\s*%\}([\s\S]*?)\{%\s*endif\s*%\}/g
  result = result.replace(ifRegex, (_, key, content) => {
    return alert[key] ? content.trim() : ''
  })

  const ifCompareRegex = /\{%\s*if\s+alert\.(\w+)\s*(==|!=|>|<|>=|<=)\s*["']?(\w+)["']?\s*%\}([\s\S]*?)\{%\s*endif\s*%\}/g
  result = result.replace(ifCompareRegex, (_, key, op, val, content) => {
    const alertVal = alert[key]
    let matches = false
    switch (op) {
      case '==': matches = String(alertVal) === val; break
      case '!=': matches = String(alertVal) !== val; break
      case '>': matches = Number(alertVal) > Number(val); break
      case '<': matches = Number(alertVal) < Number(val); break
      case '>=': matches = Number(alertVal) >= Number(val); break
      case '<=': matches = Number(alertVal) <= Number(val); break
    }
    return matches ? content.trim() : ''
  })

  result = result.replace(/\{%[^%]*%}/g, '')

  return result
}
