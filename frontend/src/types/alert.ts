export interface AlertResponse {
  id: number
  tenant_id: string
  alert_key: string
  fingerprint: string
  source: string
  title: string
  content?: string
  severity: string
  status: string
  labels: Record<string, any>
  annotations: Record<string, any>
  metric_name?: string
  metric_value?: any
  raw_data: Record<string, any>
  trace_id?: string
  fire_count: number
  repeat_count: number
  assignee_id?: number
  assignee_name?: string
  fired_at: string
  resolved_at?: string
  acknowledged_at?: string
  silenced_until?: string
  escalation_count: number
  matched_rules: any[]
  notification_channels: any[]
  created_at: string
  updated_at: string
  // 云产品字段
  namespace?: string
  instance_id?: string
  instance_name?: string
}

export interface AlertStats {
  total: number
  unique: number
  today: number
  firing_critical: number
  firing_high: number
  firing: number
  resolved: number
  suppressed: number
  critical: number
  high: number
  medium: number
  low: number
  info: number
  unassigned: number
}

export interface AlertAggregatedItem {
  fingerprint: string
  count: number
  latest: AlertResponse
}

export interface AlertFilter {
  status?: string
  severity?: string[]
  source?: string
  assignee_id?: number
  labels?: Record<string, string>
  start_time?: string
  end_time?: string
  keyword?: string
}
