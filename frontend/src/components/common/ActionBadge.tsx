import {
  AlertCircle, CheckCircle, MessageSquare, Check,
  BellOff, ExternalLink, ArrowUp, Bell, Send, Filter,
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
  // 系统自动操作
  received: { label: '接入', color: 'bg-blue-100 text-blue-700', icon: Bell },
  fired: { label: '触发', color: 'bg-red-100 text-red-700', icon: AlertCircle },
  filtered: { label: '过滤', color: 'bg-yellow-100 text-yellow-700', icon: Filter },
  escalated: { label: '升级', color: 'bg-orange-100 text-orange-700', icon: ArrowUp },
  // 人工操作
  acknowledged: { label: '确认', color: 'bg-yellow-100 text-yellow-700', icon: Check },
  resolved: { label: '恢复', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  silenced: { label: '静默', color: 'bg-gray-100 text-gray-700', icon: BellOff },
  updated: { label: '更新', color: 'bg-blue-100 text-blue-700', icon: MessageSquare },
}

function getActionConfig(action: string): ActionConfig {
  // 精确匹配
  if (actionConfigs[action]) {
    return actionConfigs[action]
  }

  // 前缀匹配（兼容旧数据）
  if (action.startsWith('escalate_level_')) {
    const level = action.replace('escalate_level_', '')
    return { label: `升级 L${level}`, color: 'bg-orange-100 text-orange-700', icon: ArrowUp }
  }

  if (action.startsWith('notification_')) {
    const channel = action.replace('notification_', '')
    return { label: `通知 (${channel})`, color: 'bg-blue-100 text-blue-700', icon: Send }
  }

  // 兼容旧的 dispose_* 类型
  if (action.startsWith('dispose_')) {
    const disposeAction = action.replace('dispose_', '')
    const disposeConfigs: Record<string, ActionConfig> = {
      note: { label: '备注', color: 'bg-blue-100 text-blue-700', icon: MessageSquare },
      acknowledge: { label: '确认', color: 'bg-yellow-100 text-yellow-700', icon: Check },
      resolve: { label: '解决', color: 'bg-green-100 text-green-700', icon: CheckCircle },
      silence: { label: '静默', color: 'bg-gray-100 text-gray-700', icon: BellOff },
    }
    if (disposeConfigs[disposeAction]) {
      return disposeConfigs[disposeAction]
    }
  }

  // 兼容旧的 callback 类型
  if (action === 'acknowledge_callback') {
    return { label: '外部确认', color: 'bg-orange-100 text-orange-700', icon: ExternalLink }
  }
  if (action === 'resolve_callback') {
    return { label: '外部恢复', color: 'bg-green-100 text-green-700', icon: ExternalLink }
  }
  if (action === 'silence_callback') {
    return { label: '外部静默', color: 'bg-gray-100 text-gray-700', icon: ExternalLink }
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
