import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuthStore } from '@/stores/auth-store'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private getAccessToken(): string | null {
    // 直接从 zustand store 访问状态，不使用 hook
    return useAuthStore.getState().accessToken
  }

  private getRefreshToken(): string | null {
    return useAuthStore.getState().refreshToken
  }

  private setupInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getAccessToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config

        if (error.response?.status === 401 && originalRequest) {
          const refreshToken = this.getRefreshToken()
          // 如果没有 refresh token，直接登出
          if (!refreshToken) {
            useAuthStore.getState().logout()
            window.location.href = '/login'
            return Promise.reject(error)
          }
          try {
            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: refreshToken,
            })
            useAuthStore.getState().setTokens(response.data.access_token, response.data.refresh_token)
            return this.client(originalRequest)
          } catch {
            useAuthStore.getState().logout()
            window.location.href = '/login'
          }
        }

        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, params?: object): Promise<T> {
    const response = await this.client.get<T>(url, { params })
    return response.data
  }

  async post<T>(url: string, data?: object): Promise<T> {
    const response = await this.client.post<T>(url, data)
    return response.data
  }

  async put<T>(url: string, data?: object): Promise<T> {
    const response = await this.client.put<T>(url, data)
    return response.data
  }

  async patch<T>(url: string, data?: object): Promise<T> {
    const response = await this.client.patch<T>(url, data)
    return response.data
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url)
    return response.data
  }
}

export const apiClient = new ApiClient()
