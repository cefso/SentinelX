import {
  AlertCircle, CheckCircle, Copy, Layers, MessageSquare, Check,
  BellOff, ExternalLink, ArrowUp, UserPlus, Bell, Send,
} from 'lucide-react'

interface ActionBadgeProps {
  action: string
  className?: string
}

interface ActionConfig {
  label: string
  color: string
  icon: React.ComponentType<{ className?: string }>
}

const actionConfigs: Record<string, ActionConfig> = {
  fired: { label: '触发', color: 'bg-red-100 text-red-700', icon: AlertCircle },
  resolved: { label: '恢复', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  received: { label: '接入', color: 'bg-blue-100 text-blue-700', icon: Bell },
  deduplicated: { label: '去重', color: 'bg-yellow-100 text-yellow-700', icon: Copy },
  aggregated: { label: '聚合', color: 'bg-purple-100 text-purple-700', icon: Layers },
  dispose_note: { label: '备注', color: 'bg-blue-100 text-blue-700', icon: MessageSquare },
  dispose_acknowledge: { label: '确认', color: 'bg-yellow-100 text-yellow-700', icon: Check },
  dispose_resolve: { label: '解决', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  dispose_silence: { label: '静默', color: 'bg-gray-100 text-gray-700', icon: BellOff },
  acknowledge_callback: { label: '外部确认', color: 'bg-orange-100 text-orange-700', icon: ExternalLink },
  resolve_callback: { label: '外部恢复', color: 'bg-green-100 text-green-700', icon: ExternalLink },
  silence_callback: { label: '外部静默', color: 'bg-gray-100 text-gray-700', icon: ExternalLink },
  auto_assign: { label: '自动分配', color: 'bg-blue-100 text-blue-700', icon: UserPlus },
  update: { label: '更新', color: 'bg-blue-100 text-blue-700', icon: MessageSquare },
}

function getActionConfig(action: string): ActionConfig {
  // 精确匹配
  if (actionConfigs[action]) {
    return actionConfigs[action]
  }

  // 前缀匹配
  if (action.startsWith('escalate_level_')) {
    const level = action.replace('escalate_level_', '')
    return { label: `升级 L${level}`, color: 'bg-orange-100 text-orange-700', icon: ArrowUp }
  }

  if (action.startsWith('notification_')) {
    const channel = action.replace('notification_', '')
    return { label: `通知 (${channel})`, color: 'bg-blue-100 text-blue-700', icon: Send }
  }

  // 默认
  return { label: action, color: 'bg-gray-100 text-gray-700', icon: AlertCircle }
}

export function ActionBadge({ action, className = '' }: ActionBadgeProps) {
  const config = getActionConfig(action)
  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.color} ${className}`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  )
}
