import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { apiClient } from '@/services/api'

interface PublicTenant {
  id: number
  name: string
  slug: string
}

export function RegisterPage() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    phone: '',
    tenant_id: '' as number | '',
  })
  const [tenants, setTenants] = useState<PublicTenant[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const navigate = useNavigate()

  // 获取公开租户列表
  useEffect(() => {
    apiClient.get<{ tenants: PublicTenant[] }>('/tenants/public')
      .then(res => setTenants(res.tenants || []))
      .catch(() => setTenants([]))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await apiClient.post('/auth/register', {
        username: formData.username,
        email: formData.email,
        password: formData.password,
        phone: formData.phone || undefined,
        tenant_id: formData.tenant_id || undefined,
      })
      setSuccess(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow text-center">
          <div className="text-6xl mb-4">📧</div>
          <h2 className="text-2xl font-bold text-gray-900">注册成功</h2>
          <p className="text-gray-600 mt-2">
            您的账号已提交注册申请，请等待系统管理员审批。
          </p>
          <p className="text-sm text-gray-500 mt-4">
            审批通过后您将收到通知，届时可使用用户名和密码登录。
          </p>
          <Link
            to="/login"
            className="inline-block mt-6 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            返回登录
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-center text-3xl font-bold">注册账号</h2>
          <p className="mt-2 text-center text-gray-600">SentinelX 综合告警平台</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="text-red-500 text-sm text-center bg-red-50 p-2 rounded">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              用户名
            </label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
              required
              minLength={3}
              maxLength={64}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              邮箱
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              密码
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              手机号（可选）
            </label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
            />
          </div>
          {tenants.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700">
                申请租户（可选）
              </label>
              <select
                value={formData.tenant_id}
                onChange={(e) => setFormData({ ...formData, tenant_id: e.target.value ? Number(e.target.value) : '' })}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
              >
                <option value="">不申请特定租户</option>
                {tenants.map((tenant) => (
                  <option key={tenant.id} value={tenant.id}>
                    {tenant.name}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-500">
                如果您需要加入特定租户，请选择对应的租户名称
              </p>
            </div>
          )}
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
          >
            {loading ? '提交中...' : '注册'}
          </button>
          <div className="text-center text-sm">
            <span className="text-gray-600">已有账号？</span>
            <Link to="/login" className="text-blue-600 hover:text-blue-700 ml-1">
              登录
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
