import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Role {
  id: number
  code: string
  name: string
}

export interface Tenant {
  id: number
  name: string
  slug: string
  role: Role
  is_current: boolean
  is_superuser: boolean
  permissions: string[]
}

interface User {
  id: number
  username: string
  email: string
  is_system: boolean
  is_superuser?: boolean
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  tenants: Tenant[]
  currentTenant: Tenant | null
  isAuthenticated: boolean

  setTokens: (accessToken: string, refreshToken: string) => void
  setUser: (user: User) => void
  setTenants: (tenants: Tenant[]) => void
  setCurrentTenant: (tenant: Tenant) => void
  switchTenant: (tenantId: number) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      tenants: [],
      currentTenant: null,
      isAuthenticated: false,

      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken, isAuthenticated: true })
      },

      setUser: (user) => {
        set({ user })
      },

      setTenants: (tenants) => {
        const currentTenant = tenants.find(t => t.is_current) || tenants[0] || null
        set({ tenants, currentTenant })
      },

      setCurrentTenant: (tenant) => {
        // 更新租户的 is_current 状态
        const tenants = get().tenants.map(t => ({
          ...t,
          is_current: t.id === tenant.id
        }))
        set({ tenants, currentTenant: tenant })
      },

      switchTenant: async (tenantId: number) => {
        const { accessToken } = get()
        if (!accessToken) {
          throw new Error('Not authenticated')
        }

        // 使用动态 import 避免循环依赖
        const { apiClient } = await import('@/services/api')
        const data = await apiClient.post<{
          access_token: string
          refresh_token: string
          user?: User
          tenants?: Tenant[]
        }>('/auth/switch-tenant', { tenant_id: tenantId })

        // 更新 tokens
        set({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          isAuthenticated: true
        })

        // 更新用户和租户信息
        if (data.user) {
          set({ user: data.user })
        }
        if (data.tenants) {
          const currentTenant = data.tenants.find((t: Tenant) => t.is_current) || data.tenants[0]
          set({
            tenants: data.tenants,
            currentTenant
          })
        }
      },

      logout: () => {
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          tenants: [],
          currentTenant: null,
          isAuthenticated: false,
        })
      },
    }),
    {
      name: 'sentinelx-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        tenants: state.tenants,
        currentTenant: state.currentTenant,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// 导出 getState 用于非 hook 上下文
export const getAuthState = useAuthStore.getState
