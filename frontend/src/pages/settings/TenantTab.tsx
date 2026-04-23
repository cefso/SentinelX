import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'

interface Tenant {
  id: number
  name: string
  slug: string
  max_alerts: number
  max_users: number
  max_rules: number
  max_channels: number
  alert_qps: number
  is_active: boolean
  config: Record<string, any>
  webhook_url?: string
}

export function TenantTab() {
  const { user } = useAuthStore()
  const { data: tenant } = useQuery<Tenant>({
    queryKey: ['currentTenant'],
    queryFn: () => apiClient.get('/tenants/current'),
  })

  return (
    <div className="space-y-6">
      {/* 当前租户信息 */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-medium mb-1">当前租户</h3>
            <p className="text-sm text-gray-500">查看租户配置</p>
          </div>
        </div>

        {!tenant ? (
          <div className="p-8 text-center">加载中...</div>
        ) : (
          <dl className="space-y-4">
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">租户名称</dt>
              <dd className="text-sm font-medium">{tenant.name}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">Slug</dt>
              <dd className="text-sm font-mono">{tenant.slug}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">告警配额</dt>
              <dd className="text-sm font-medium">{tenant.max_alerts.toLocaleString()}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">用户配额</dt>
              <dd className="text-sm font-medium">{tenant.max_users}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">规则配额</dt>
              <dd className="text-sm font-medium">{tenant.max_rules}</dd>
            </div>
            <div className="flex items-center justify-between py-3 border-b">
              <dt className="text-sm text-gray-500">渠道配额</dt>
              <dd className="text-sm font-medium">{tenant.max_channels}</dd>
            </div>
            <div className="flex items-center justify-between py-3">
              <dt className="text-sm text-gray-500">告警QPS</dt>
              <dd className="text-sm font-medium">{tenant.alert_qps}</dd>
            </div>
            {tenant.webhook_url && (
              <div className="flex items-center justify-between py-3 border-t">
                <dt className="text-sm text-gray-500">Webhook URL</dt>
                <dd className="text-sm font-mono text-blue-600">{tenant.webhook_url}</dd>
              </div>
            )}
          </dl>
        )}
      </div>

      {/* 租户列表（仅系统管理员可见） */}
      {user?.is_system === true && <TenantList />}
    </div>
  )
}

function TenantList() {
  const queryClient = useQueryClient()
  const { data: tenants = [] } = useQuery<Tenant[]>({
    queryKey: ['tenants'],
    queryFn: () => apiClient.get('/tenants'),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiClient.put(`/tenants/${id}`, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
    },
  })

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-4">所有租户</h3>
      {tenants.length === 0 ? (
        <div className="p-8 text-center text-gray-500">暂无租户</div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="text-left text-sm text-gray-500 border-b">
              <th className="pb-3 font-medium">名称</th>
              <th className="pb-3 font-medium">Slug</th>
              <th className="pb-3 font-medium">启用</th>
              <th className="pb-3 font-medium">告警配额</th>
              <th className="pb-3 font-medium">用户配额</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {tenants.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50">
                <td className="py-3 font-medium">{t.name}</td>
                <td className="py-3 font-mono text-sm text-gray-500">{t.slug}</td>
                <td className="py-3">
                  <button
                    onClick={() => toggleMutation.mutate({ id: t.id, is_active: !t.is_active })}
                    disabled={toggleMutation.isPending}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50 ${
                      t.is_active ? 'bg-blue-600' : 'bg-gray-300'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        t.is_active ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </td>
                <td className="py-3 text-sm">{t.max_alerts.toLocaleString()}</td>
                <td className="py-3 text-sm">{t.max_users}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
