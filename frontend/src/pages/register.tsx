import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { apiClient } from '@/services/api'
import { registerSchema, type RegisterFormData } from '@/schemas'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface PublicTenant {
  id: number
  name: string
  slug: string
}

export function RegisterPage() {
  const [tenants, setTenants] = useState<PublicTenant[]>([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: '',
      email: '',
      password: '',
      phone: '',
    },
  })

  useEffect(() => {
    apiClient.get<{ tenants: PublicTenant[] }>('/tenants/public')
      .then(res => setTenants(res.tenants || []))
      .catch(() => setTenants([]))
  }, [])

  const onSubmit = async (data: RegisterFormData) => {
    setError('')
    try {
      await apiClient.post('/auth/register', {
        ...data,
        phone: data.phone || undefined,
        tenant_id: data.tenant_id || undefined,
      })
      setSuccess(true)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed')
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-6 space-y-4">
            <div className="text-6xl mb-4">📧</div>
            <h2 className="text-2xl font-bold">注册成功</h2>
            <p className="text-muted-foreground">
              您的账号已提交注册申请，请等待系统管理员审批。
            </p>
            <p className="text-sm text-muted-foreground">
              审批通过后您将收到通知，届时可使用用户名和密码登录。
            </p>
            <Link to="/login">
              <Button className="mt-4">返回登录</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-bold">注册账号</CardTitle>
          <CardDescription>SentinelX 综合告警平台</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
            {error && (
              <div className="text-sm text-destructive bg-destructive/10 p-3 rounded-md">{error}</div>
            )}
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
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                type="email"
                placeholder="请输入邮箱"
                {...register('email')}
              />
              {errors.email && (
                <p className="text-sm text-destructive">{errors.email.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="请输入密码"
                {...register('password')}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">手机号（可选）</Label>
              <Input
                id="phone"
                type="tel"
                placeholder="请输入手机号"
                {...register('phone')}
              />
            </div>
            {tenants.length > 0 && (
              <div className="space-y-2">
                <Label>申请租户（可选）</Label>
                <Select onValueChange={(value) => setValue('tenant_id', value ? Number(value) : undefined)}>
                  <SelectTrigger>
                    <SelectValue placeholder="不申请特定租户" />
                  </SelectTrigger>
                  <SelectContent>
                    {tenants.map((tenant) => (
                      <SelectItem key={tenant.id} value={String(tenant.id)}>
                        {tenant.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  如果您需要加入特定租户，请选择对应的租户名称
                </p>
              </div>
            )}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? '提交中...' : '注册'}
            </Button>
            <div className="text-center text-sm">
              <span className="text-muted-foreground">已有账号？</span>
              <Link to="/login" className="text-primary hover:underline ml-1">
                登录
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
