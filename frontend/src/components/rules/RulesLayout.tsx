import { Link, useLocation } from 'react-router-dom'
import { GitBranch, ShieldOff, Layers, Route } from 'lucide-react'

interface RulesLayoutProps {
  children: React.ReactNode
}

const tabs = [
  { key: 'routes', label: '路由规则', href: '/rules', icon: Route, color: 'blue' },
  { key: 'dedup', label: '去重规则', href: '/rules/dedup', icon: GitBranch, color: 'amber' },
  { key: 'suppress', label: '抑制规则', href: '/rules/suppress', icon: ShieldOff, color: 'rose' },
  { key: 'aggregate', label: '聚合规则', href: '/rules/aggregate', icon: Layers, color: 'violet' },
]

export function RulesLayout({ children }: RulesLayoutProps) {
  const location = useLocation()

  const getActiveTab = () => {
    if (location.pathname === '/rules') return 'routes'
    if (location.pathname === '/rules/dedup') return 'dedup'
    if (location.pathname === '/rules/suppress') return 'suppress'
    if (location.pathname === '/rules/aggregate') return 'aggregate'
    return 'routes'
  }

  const activeTab = getActiveTab()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">规则管理</h1>
        <p className="text-gray-600">配置告警路由、去重、抑制和聚合策略</p>
      </div>

      <div className="border-b border-gray-200">
        <nav className="flex gap-1 -mb-px">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.key
            const colorClasses: Record<string, string> = {
              blue: 'border-blue-500 text-blue-600 bg-blue-50',
              amber: 'border-amber-500 text-amber-600 bg-amber-50',
              rose: 'border-rose-500 text-rose-600 bg-rose-50',
              violet: 'border-violet-500 text-violet-600 bg-violet-50',
            }
            const activeClass = colorClasses[tab.color] || colorClasses.blue

            return (
              <Link
                key={tab.key}
                to={tab.href}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  isActive
                    ? `${activeClass} rounded-t-md`
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </Link>
            )
          })}
        </nav>
      </div>

      {children}
    </div>
  )
}
