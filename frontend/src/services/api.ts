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

  async post<T>(url: string, data?: object, options?: { timeout?: number }): Promise<T> {
    const response = await this.client.post<T>(url, data, {
      timeout: options?.timeout,
    })
    return response.data
  }

  /** 提交告警 AI 异步任务（立即返回 202 + task_id） */
  async submitAlertAiTask(url: string, data?: object): Promise<AITaskCreateResponse> {
    return this.post<AITaskCreateResponse>(url, data, { timeout: 15_000 })
  }

  async getAiTask(taskId: string): Promise<AITaskStatusResponse> {
    return this.get<AITaskStatusResponse>(`/ai/tasks/${taskId}`)
  }

  /** 轮询异步任务直至完成或失败 */
  async pollAiTask(
    taskId: string,
    options?: { intervalMs?: number; maxAttempts?: number; onStatus?: (status: string) => void },
  ): Promise<AITaskStatusResponse> {
    const intervalMs = options?.intervalMs ?? 2000
    const maxAttempts = options?.maxAttempts ?? 120

    for (let i = 0; i < maxAttempts; i++) {
      const task = await this.getAiTask(taskId)
      options?.onStatus?.(task.status)
      if (task.status === 'completed') return task
      if (task.status === 'failed') {
        throw new Error(task.error || 'AI任务失败')
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs))
    }
    throw new Error('AI分析仍在进行，请稍后刷新页面重试')
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

  async getAiConfig(): Promise<AIConfigResponse> {
    return this.get('/ai/config')
  }

  async updateAiConfig(data: AIConfigUpdate): Promise<AIConfigResponse> {
    return this.put('/ai/config', data)
  }

  async listAiProviders(): Promise<AIProvidersListResponse> {
    return this.get('/ai/providers')
  }

  async listAiModels(data: ListAiModelsRequest): Promise<ListAiModelsResponse> {
    return this.post('/ai/models', data, { timeout: 60_000 })
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

export interface AIModelInfo {
  id: string
  name?: string
}

export interface AIProviderMeta {
  id: string
  name: string
  description?: string
  default_base_url?: string
  requires_base_url: boolean
  openai_compatible: boolean
}

export interface AIPromptMeta {
  key: string
  title: string
  description?: string
}

export interface AIConfigResponse {
  provider_id: string
  display_name: string
  base_url?: string | null
  model: string
  api_key_set: boolean
  enabled: boolean
  prompts?: Record<string, string | null>
  prompt_defaults?: Record<string, string>
  prompt_meta?: AIPromptMeta[]
}

export interface AIConfigUpdate {
  provider_id: string
  display_name?: string
  base_url?: string
  model: string
  api_key?: string
  enabled: boolean
  prompts?: Record<string, string | null>
}

export interface ListAiModelsRequest {
  provider_id: string
  api_key?: string
  base_url?: string
}

export interface ListAiModelsResponse {
  models: AIModelInfo[]
}

export interface AIProvidersListResponse {
  providers: AIProviderMeta[]
}

export interface AITaskCreateResponse {
  task_id: string
  status: string
  alert_id: number
  action: string
}

export interface AITaskStatusResponse {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | string
  alert_id: number
  action: string
  result?: Record<string, unknown>
  error?: string | null
  created_at?: string
  updated_at?: string
}

export const apiClient = new ApiClient()
