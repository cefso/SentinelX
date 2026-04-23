import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useAuthStore } from '@/stores/auth-store'
import { apiClient } from '@/services/api'
import { toast } from '@/stores/toast-store'
import { Eye, EyeOff } from 'lucide-react'
import { loginSchema, type LoginFormData } from '@/schemas'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

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
  const [showPassword, setShowPassword] = useState(false)
  const navigate = useNavigate()
  const { setTokens, setUser, setTenants } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    try {
      const response = await apiClient.post<LoginResponse>('/auth/login', data)
      setTokens(response.access_token, response.refresh_token)
      setUser(response.user)
      setTenants(response.tenants)
      navigate('/')
    } catch (err: unknown) {
      const errorMessage =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        '登录失败，请检查用户名和密码'
      toast.error(errorMessage)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-3xl font-bold">SentinelX</CardTitle>
          <CardDescription>综合告警平台</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
            <div className="space-y-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                type="text"
                placeholder="请输入用户名"
                {...register('username')}
              />
              {errors.username && (
                <p className="text-sm text-destructive">{errors.username.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="请输入密码"
                  {...register('password')}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? '登录中...' : '登录'}
            </Button>
            <div className="text-center text-sm">
              <span className="text-muted-foreground">没有账户？</span>
              <Link to="/register" className="text-primary hover:underline ml-1">
                注册
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
