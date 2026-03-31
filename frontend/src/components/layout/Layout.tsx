import { useState, useRef, useEffect } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { Settings, LogOut, UserCircle, ChevronDown, Bell, Settings2, Send, Search, Plug, Check, Building2 } from 'lucide-react'

const navigation = [
  { name: '告警', href: '/alerts', icon: Bell },
  { name: '规则', href: '/rules', icon: Settings2 },
  { name: '渠道', href: '/channels', icon: Send },
  { name: '诊断', href: '/diagnose', icon: Search },
]

const bottomNavigation = [
  { name: '告警提供商', href: '/alerts/sources', icon: Plug },
]

export function Layout() {
  const location = useLocation()
  const { user, tenants, currentTenant, switchTenant, logout } = useAuthStore()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showTenantMenu, setShowTenantMenu] = useState(false)
  const [switching, setSwitching] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const tenantMenuRef = useRef<HTMLDivElement>(null)

  // 点击外部关闭菜单
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false)
      }
      if (tenantMenuRef.current && !tenantMenuRef.current.contains(event.target as Node)) {
        setShowTenantMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleTenantSwitch = async (tenantId: number) => {
    if (tenantId === currentTenant?.id) {
      setShowTenantMenu(false)
      return
    }
    setSwitching(true)
    try {
      await switchTenant(tenantId)
      setShowTenantMenu(false)
    } catch (error) {
      console.error('Failed to switch tenant:', error)
    } finally {
      setSwitching(false)
    }
  }

  return (
    <div className="h-screen flex overflow-hidden">
      <aside className="w-64 bg-gray-900 text-white flex flex-col overflow-y-auto">
        <div className="h-16 flex items-center px-6 border-b border-gray-800 shrink-0">
          <h1 className="text-xl font-bold">SentinelX</h1>
        </div>
        <nav className="p-4 space-y-1 flex-1">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname.startsWith(item.href)
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-4 py-2 rounded-md ${
                  isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800'
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>
        <div className="mt-auto border-t border-gray-800">
          {/* 告警提供商 */}
          <nav className="p-2 space-y-1">
            {bottomNavigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname.startsWith(item.href)
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-4 py-2 rounded-md ${
                    isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* 用户信息区域 */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="w-full p-4 flex items-center justify-between hover:bg-gray-800 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center shrink-0">
                  <UserCircle className="w-6 h-6 text-gray-400" />
                </div>
                <div className="text-sm font-medium truncate">{user?.username}</div>
              </div>
              <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
            </button>

            {showUserMenu && (
              <div className="absolute bottom-full left-0 right-0 mb-1 py-1 bg-gray-800 rounded-lg shadow-lg border border-gray-700">
                <Link
                  to="/settings"
                  onClick={() => setShowUserMenu(false)}
                  className="flex items-center gap-3 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white"
                >
                  <Settings className="w-4 h-4" />
                  设置
                </Link>
                <button
                  onClick={() => {
                    setShowUserMenu(false)
                    logout()
                  }}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white"
                >
                  <LogOut className="w-4 h-4" />
                  退出
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>
      <main className="flex-1 bg-gray-50 flex flex-col overflow-hidden">
        {/* 顶部导航栏 */}
        <header className="h-14 bg-white border-b border-gray-200 px-6 flex items-center justify-end shrink-0">
          {/* 租户切换 */}
          {tenants.length > 0 && (
            <div className="relative" ref={tenantMenuRef}>
              <button
                onClick={() => setShowTenantMenu(!showTenantMenu)}
                disabled={switching}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md hover:bg-gray-100 transition-colors disabled:opacity-50"
              >
                <div className="w-7 h-7 rounded bg-blue-600 flex items-center justify-center shrink-0">
                  <Building2 className="w-4 h-4 text-white" />
                </div>
                <div className="text-left">
                  <div className="text-sm font-medium text-gray-900">{currentTenant?.name || '选择租户'}</div>
                  <div className="text-xs text-gray-500">{currentTenant?.role?.name}</div>
                </div>
                <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showTenantMenu ? 'rotate-180' : ''}`} />
              </button>

              {showTenantMenu && (
                <div className="absolute right-0 top-full mt-1 py-1 bg-white rounded-lg shadow-lg border border-gray-200 w-64 max-h-64 overflow-y-auto z-50">
                  {tenants.map((tenant) => (
                    <button
                      key={tenant.id}
                      onClick={() => handleTenantSwitch(tenant.id)}
                      disabled={switching}
                      className="w-full flex items-center justify-between px-4 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <Building2 className="w-4 h-4 text-gray-400 shrink-0" />
                        <div className="text-left min-w-0">
                          <div className="font-medium text-gray-900 truncate">{tenant.name}</div>
                          <div className="text-xs text-gray-500 truncate">{tenant.role?.name}</div>
                        </div>
                      </div>
                      {tenant.is_current && <Check className="w-4 h-4 text-green-500 shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </header>
        {/* 内容区域 */}
        <div className="flex-1 p-6 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
