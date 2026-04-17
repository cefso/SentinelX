import { useState, useRef, useEffect } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { useUIStore } from '@/stores/ui-store'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { Settings, LogOut, UserCircle, ChevronDown, Bell, Settings2, Send, Search, Plug, Check, Building2, Plus, PanelLeftClose, PanelLeft, BarChart3 } from 'lucide-react'

const navigation = [
  { name: '告警', href: '/alerts', icon: Bell },
  { name: '规则', href: '/rules', icon: Settings2 },
  { name: '渠道', href: '/channels', icon: Send },
  { name: '云指标', href: '/cloud-metrics', icon: BarChart3 },
  { name: '诊断', href: '/diagnose', icon: Search },
]

const bottomNavigation = [
  { name: '告警提供商', href: '/alerts/sources', icon: Plug },
]

export function Layout() {
  const location = useLocation()
  const queryClient = useQueryClient()
  const { user, tenants, currentTenant, switchTenant, logout } = useAuthStore()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showTenantMenu, setShowTenantMenu] = useState(false)
  const [showCreateTenantModal, setShowCreateTenantModal] = useState(false)
  const [switching, setSwitching] = useState(false)
  const { sidebarCollapsed, setSidebarCollapsed } = useUIStore()
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
      // 切换成功后刷新所有租户相关的数据
      await queryClient.invalidateQueries()
      // 强制刷新当前页面
      window.location.reload()
    } catch (error) {
      console.error('Failed to switch tenant:', error)
    } finally {
      setSwitching(false)
    }
  }

  return (
    <div className="h-screen flex overflow-hidden">
      <aside className={`bg-gray-900 text-white flex flex-col overflow-y-auto shrink-0 transition-all duration-200 z-10 ${sidebarCollapsed ? 'w-16' : 'w-64'}`}>
        <div className="h-16 flex items-center border-b border-gray-800 shrink-0">
          {!sidebarCollapsed && (
            <h1 className="text-xl font-bold px-6">SentinelX</h1>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-4 hover:bg-gray-800 transition-colors ml-auto"
            title={sidebarCollapsed ? '展开侧边栏' : '折叠侧边栏'}
          >
            {sidebarCollapsed ? <PanelLeft className="w-5 h-5 text-gray-400" /> : <PanelLeftClose className="w-5 h-5 text-gray-400" />}
          </button>
        </div>
        <nav className={`p-4 space-y-1 flex-1 ${sidebarCollapsed ? 'px-2' : ''}`}>
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname.startsWith(item.href)
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-4 py-2 rounded-md ${
                  isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800'
                } ${sidebarCollapsed ? 'justify-center px-2' : ''}`}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <Icon className="w-5 h-5 shrink-0" />
                {!sidebarCollapsed && item.name}
              </Link>
            )
          })}
        </nav>
        <div className="mt-auto border-t border-gray-800">
          {/* 告警提供商 */}
          <nav className={`p-2 space-y-1 ${sidebarCollapsed ? 'px-2' : ''}`}>
            {bottomNavigation.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname.startsWith(item.href)
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center gap-3 px-4 py-2 rounded-md ${
                    isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800'
                  } ${sidebarCollapsed ? 'justify-center px-2' : ''}`}
                  title={sidebarCollapsed ? item.name : undefined}
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  {!sidebarCollapsed && item.name}
                </Link>
              )
            })}
          </nav>

          {/* 用户信息区域 */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className={`w-full hover:bg-gray-800 transition-colors flex items-center ${sidebarCollapsed ? 'justify-center p-3' : 'p-4 justify-between'}`}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center shrink-0">
                  <UserCircle className="w-6 h-6 text-gray-400" />
                </div>
                {!sidebarCollapsed && (
                  <div className="text-sm font-medium truncate">{user?.username}</div>
                )}
              </div>
              {!sidebarCollapsed && (
                <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
              )}
            </button>

            {showUserMenu && (
              <div className={`absolute bottom-full mb-1 py-1 bg-gray-800 rounded-lg shadow-lg border border-gray-700 ${sidebarCollapsed ? 'left-0 w-48' : 'left-0 right-0'}`}>
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
        <header className="h-14 bg-white border-b border-gray-200 px-6 flex items-center justify-end gap-4 shrink-0">
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
                <div className="absolute right-0 top-full mt-1 py-1 bg-white rounded-lg shadow-lg border border-gray-200 w-64 max-h-80 overflow-y-auto z-50">
                  {user?.is_system === true && (
                    <button
                      onClick={() => {
                        setShowTenantMenu(false)
                        setShowCreateTenantModal(true)
                      }}
                      className="w-full flex items-center gap-3 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 border-b border-gray-100"
                    >
                      <Plus className="w-4 h-4" />
                      <span className="font-medium">新增租户</span>
                    </button>
                  )}
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
          <Outlet key={location.pathname} />
        </div>

        {/* 创建租户 Modal */}
        {showCreateTenantModal && (
          <CreateTenantModal
            onClose={() => setShowCreateTenantModal(false)}
            onSuccess={() => {
              setShowCreateTenantModal(false)
            }}
          />
        )}
      </main>
    </div>
  )
}

// ============ 创建租户 Modal ============
function CreateTenantModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const { setTenants } = useAuthStore()
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    max_alerts: 10000,
    max_users: 10,
    max_rules: 100,
    max_channels: 20,
    alert_qps: 100,
  })
  const [error, setError] = useState('')

  const createMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      await apiClient.post('/tenants', data)
      // 刷新用户的租户列表
      const tenantsRes = await apiClient.get<{ tenants: any[] }>('/auth/tenants')
      setTenants(tenantsRes.tenants)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
      onSuccess()
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || '创建失败')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    createMutation.mutate(formData)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-lg">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold">创建新租户</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">租户名称</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="如: 生产环境"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Slug</label>
            <input
              type="text"
              required
              pattern="^[a-z0-9-]+$"
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-') })}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="如: production"
            />
            <p className="text-xs text-gray-500 mt-1">只能包含小写字母、数字和连字符</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">告警配额</label>
              <input
                type="number"
                value={formData.max_alerts}
                onChange={(e) => setFormData({ ...formData, max_alerts: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">用户配额</label>
              <input
                type="number"
                value={formData.max_users}
                onChange={(e) => setFormData({ ...formData, max_users: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">规则配额</label>
              <input
                type="number"
                value={formData.max_rules}
                onChange={(e) => setFormData({ ...formData, max_rules: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">渠道配额</label>
              <input
                type="number"
                value={formData.max_channels}
                onChange={(e) => setFormData({ ...formData, max_channels: parseInt(e.target.value) || 0 })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded">{error}</div>
          )}

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-lg hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
