/** 抑制规则在 DB 中的 suppress_config 占位（条件统一存于 rule.conditions） */
export function buildSuppressConfigPayload(durationMinutes: number = 0): Record<string, unknown> {
  return {
    enabled: true,
    type: 'rule_based',
    duration_minutes: durationMinutes,
    rule_based: { conditions: [], delay_seconds: 0 },
  }
}

/** 编辑旧规则时，将曾写在 suppress_config 内的条件合并进表单 */
export function mergeLegacySuppressConditions(
  ruleConditions: Array<{ field: string; operator: string; value?: unknown }>,
  apiConfig: Record<string, unknown> | null | undefined,
): Array<{ field: string; operator: string; value?: unknown }> {
  if (ruleConditions.length > 0) return ruleConditions
  if (!apiConfig) return []
  const rb = (apiConfig.rule_based as { conditions?: typeof ruleConditions }) || {}
  const legacy = (apiConfig.conditions as typeof ruleConditions) || []
  return rb.conditions?.length ? rb.conditions : legacy
}

export function getDurationMinutesFromConfig(
  apiConfig: Record<string, unknown> | null | undefined,
): number {
  if (!apiConfig) return 0
  const n = Number(apiConfig.duration_minutes)
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0
}

export function formatEffectiveUntilLocal(iso: string | null | undefined): string | null {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleString(undefined, {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const SUPPRESS_DURATION_HELP =
  '从规则保存时刻起生效；窗口内匹配告警显示为抑制；到期后新 ALERT 正常告警；窗口过期不会把已抑制改回告警；收到恢复(OK) 时，同指纹的抑制记录也会变为已恢复。修改时长将重新开启一段完整窗口。'

export type SuppressStatusBadge = { label: string; className: string }

/** 列表「状态」列：区分手动停用、窗口过期与生效中 */
export function getSuppressStatusBadge(rule: {
  is_active: boolean
  config?: Record<string, unknown> | null
  suppress_in_effect?: boolean | null
}): SuppressStatusBadge {
  if (!rule.is_active) {
    return { label: '停用', className: 'bg-gray-100 text-gray-800' }
  }
  const minutes = getDurationMinutesFromConfig(rule.config)
  if (minutes <= 0) {
    return { label: '永久生效', className: 'bg-green-100 text-green-800' }
  }
  if (rule.suppress_in_effect === false) {
    return { label: '已过期', className: 'bg-amber-100 text-amber-800' }
  }
  return { label: '生效中', className: 'bg-green-100 text-green-800' }
}
