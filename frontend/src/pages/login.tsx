import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import { apiClient } from '@/services/api'

interface LoginResponse {
  access_token: string
  refresh_token: string
  expires_in: number
  user: {
    id: number
    username: string
    email: string
    is_system: boolean
  }
  tenants: Array<{
    id: number
    name: string
    slug: string
    role: {
      id: number
      code: string
      name: string
    }
    is_current: boolean
    is_superuser: boolean
    permissions: string[]
  }>
}

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { setTokens, setUser, setTenants } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    console.log('Login: form submitted', { username, password })
    setError('')
    setLoading(true)

    try {
      console.log('Login: sending request to /auth/login')
      const response = await apiClient.post<LoginResponse>('/auth/login', { username, password })

      // 设置 tokens
      setTokens(response.access_token, response.refresh_token)

      // 设置用户信息
      setUser(response.user)

      // 设置租户列表
      setTenants(response.tenants)

      navigate('/')
    } catch (err: any) {
      console.error('Login error:', err)
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-center text-3xl font-bold">SentinelX</h2>
          <p className="mt-2 text-center text-gray-600">综合告警平台</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="text-red-500 text-sm text-center">{error}</div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
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
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary focus:border-primary"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
      </div>
    </div>
  )
}
