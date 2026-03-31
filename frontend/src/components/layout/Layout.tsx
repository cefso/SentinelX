import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'

const navigation = [
  { name: '告警', href: '/alerts', icon: 'bell' },
  { name: '规则', href: '/rules', icon: 'settings' },
  { name: '渠道', href: '/channels', icon: 'send' },
  { name: '诊断', href: '/diagnose', icon: 'search' },
  { name: '设置', href: '/settings', icon: 'user' },
]

export function Layout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()

  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-gray-800">
          <h1 className="text-xl font-bold">SentinelX</h1>
        </div>
        <nav className="p-4 space-y-1 flex-1">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.href)
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`block px-4 py-2 rounded-md ${
                  isActive ? 'bg-gray-800 text-white' : 'text-gray-300 hover:bg-gray-800'
                }`}
              >
                {item.name}
              </Link>
            )
          })}
        </nav>
        <div className="p-4 border-t border-gray-800">
          <div className="flex items-center justify-between">
            <div className="text-sm">
              <div className="font-medium">{user?.username}</div>
              <div className="text-gray-500">{user?.email}</div>
            </div>
            <button
              onClick={logout}
              className="text-sm text-gray-400 hover:text-white"
            >
              退出
            </button>
          </div>
        </div>
      </aside>
      <main className="flex-1 bg-gray-50 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
