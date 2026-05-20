import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuthStore } from '@/stores/auth-store'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

// FastAPI expects repeated query params for arrays: ?severity=critical&severity=high
const paramsSerializer = (params: Record<string, any>) => {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      value.forEach(v => searchParams.append(key, v))
    } else if (value !== undefined && value !== null) {
      searchParams.append(key, String(value))
    }
  }
  return searchParams.toString()
}

class ApiClient {
  private client: AxiosInstance
  private isRefreshing = false
  private refreshQueue: Array<() => void> = []

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
      paramsSerializer,
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
          // 如果已经在刷新中，将请求加入队列等待
          if (this.isRefreshing) {
            return new Promise((resolve) => {
              this.refreshQueue.push(() => {
                resolve(this.client(originalRequest))
              })
            })
          }

          this.isRefreshing = true

          const refreshToken = this.getRefreshToken()
          // 如果没有 refresh token，直接登出
          if (!refreshToken) {
            this.isRefreshing = false
            useAuthStore.getState().logout()
            window.location.href = '/login'
            return Promise.reject(error)
          }

          try {
            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: refreshToken,
            })
            useAuthStore.getState().setTokens(response.data.access_token, response.data.refresh_token)

            // 重试队列中的所有请求
            this.refreshQueue.forEach(cb => cb())
            this.refreshQueue = []

            return this.client(originalRequest)
          } catch {
            // 刷新失败，清空队列并登出
            this.refreshQueue = []
            useAuthStore.getState().logout()
            window.location.href = '/login'
          } finally {
            this.isRefreshing = false
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

  async getRuleFieldValues(params: { field: string; search?: string; limit?: number; offset?: number }): Promise<{ field: string; values: { value: string; count: number }[]; total: number }> {
    return this.get('/rules/field-values', params)
  }

  async getCloudMetricsMap(): Promise<Record<string, CloudMetricRecord[]>> {
    // 与后端 page_size 上限对齐（main 为 100；PR-1 合并后可改为 1000）
    const pageSize = 100
    const metrics: CloudMetricRecord[] = []
    let page = 1
    let total = 0

    do {
      const response = await this.get<CloudMetricsListResponse>('/cloud-metrics', {
        page,
        page_size: pageSize,
        status: 'all',
      })
      metrics.push(...response.items)
      total = response.total
      page += 1
    } while (metrics.length < total)

    const map: Record<string, CloudMetricRecord[]> = {}
    for (const m of metrics) {
      if (!map[m.namespace]) map[m.namespace] = []
      map[m.namespace].push(m)
    }
    return map
  }

  async getCloudMetrics(params?: { page?: number; page_size?: number; product?: string; namespace?: string; status?: 'all' | 'active' | 'inactive' }): Promise<CloudMetricsListResponse> {
    return this.get('/cloud-metrics', params)
  }

  async getCloudMetric(id: number): Promise<CloudMetricRecord> {
    return this.get(`/cloud-metrics/${id}`)
  }

  async createCloudMetric(data: CloudProductMetricInput): Promise<CloudMetricRecord> {
    return this.post('/cloud-metrics', data)
  }

  async updateCloudMetric(id: number, data: Partial<CloudProductMetricInput>): Promise<CloudMetricRecord> {
    return this.put(`/cloud-metrics/${id}`, data)
  }

  async deleteCloudMetric(id: number): Promise<void> {
    return this.delete(`/cloud-metrics/${id}`)
  }

  async batchDeleteCloudMetrics(ids: number[]): Promise<void> {
    return this.post('/cloud-metrics/batch-delete', ids)
  }

  async syncAllCloudMetrics(): Promise<{ message: string }> {
    return this.post('/cloud-metrics/sync-all', {})
  }
}

export interface CloudMetricRecord {
  id: number
  product: string
  namespace: string
  metric_name: string
  metric_desc?: string
  namespace_desc?: string
  metric_name_desc?: string
  unit?: string
  dimensions?: string[]
  is_active: number
}

export interface CloudProductMetricInput {
  product: string
  namespace: string
  metric_name: string
  metric_desc?: string
  namespace_desc?: string
  metric_name_desc?: string
  unit?: string
  is_active: number
}

export interface CloudMetricsListResponse {
  items: CloudMetricRecord[]
  total: number
  page: number
  page_size: number
}

export const apiClient = new ApiClient()
