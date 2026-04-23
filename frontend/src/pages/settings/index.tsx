import { useState } from 'react'
import { useAuthStore } from '@/stores/auth-store'
import { User, Lock, Shield, Key, Users, Sparkles, Info, ShieldCheck } from 'lucide-react'
import { ProfileTab } from './ProfileTab'
import { SecurityTab } from './SecurityTab'
import { TenantTab } from './TenantTab'
import { ApiKeysTab } from './ApiKeysTab'
import { UsersTab, PendingUsersTab } from './UsersTab'
import { AISettingsTab } from './AiTab'
import { AboutTab } from './AboutTab'

type SettingsTab = 'profile' | 'security' | 'tenant' | 'api-keys' | 'users' | 'ai' | 'about' | 'pending'

const menuItems = [
  { key: 'profile' as const, label: '个人信息', icon: User },
  { key: 'security' as const, label: '安全设置', icon: Lock },
  { key: 'tenant' as const, label: '租户设置', icon: Shield },
  { key: 'api-keys' as const, label: 'API Keys', icon: Key },
  { key: 'users' as const, label: '用户管理', icon: Users },
  { key: 'ai' as const, label: 'AI设置', icon: Sparkles },
  { key: 'about' as const, label: '关于本系统', icon: Info },
]

// 系统管理员专属菜单
const adminMenuItems = [
  { key: 'pending' as const, label: '待审批用户', icon: ShieldCheck },
]

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile')
  const { user } = useAuthStore()

  return (
    <div className="flex h-[calc(100vh-64px)]">
      {/* 左侧导航 */}
      <div className="w-56 border-r bg-white shrink-0">
        <div className="p-4 border-b">
          <h2 className="text-lg font-semibold text-gray-900">系统设置</h2>
        </div>
        <nav className="p-2 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon
            return (
              <button
                key={item.key}
                onClick={() => setActiveTab(item.key)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === item.key
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </button>
            )
          })}
          {user?.is_system === true && (
            <>
              <div className="my-2 border-t" />
              {adminMenuItems.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.key}
                    onClick={() => setActiveTab(item.key)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === item.key
                        ? 'bg-blue-50 text-blue-600'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    {item.label}
                  </button>
                )
              })}
            </>
          )}
        </nav>
      </div>

      {/* 右侧内容 */}
      <div className="flex-1 overflow-auto bg-gray-50 p-4 md:p-6 lg:p-8">
        {/* 内容区域 */}
        <div className="max-w-full">
          {activeTab === 'profile' && <ProfileTab />}
          {activeTab === 'security' && <SecurityTab />}
          {activeTab === 'tenant' && <TenantTab />}
          {activeTab === 'api-keys' && <ApiKeysTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'ai' && <AISettingsTab />}
          {activeTab === 'about' && <AboutTab />}
          {activeTab === 'pending' && <PendingUsersTab />}
        </div>
      </div>
    </div>
  )
}
