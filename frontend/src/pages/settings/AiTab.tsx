import { useEffect, useState } from 'react'
import { apiClient, type AIConfigResponse, type AIProviderMeta, type AIModelInfo } from '@/services/api'

export function AISettingsTab() {
  const [providers, setProviders] = useState<AIProviderMeta[]>([])
  const [providerId, setProviderId] = useState('openai')
  const [displayName, setDisplayName] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [apiKeySet, setApiKeySet] = useState(false)
  const [model, setModel] = useState('')
  const [models, setModels] = useState<AIModelInfo[]>([])
  const [enabled, setEnabled] = useState(false)
  const [loading, setLoading] = useState(true)
  const [modelsLoading, setModelsLoading] = useState(false)
  const [modelsError, setModelsError] = useState('')
  const [saveError, setSaveError] = useState('')
  const [saved, setSaved] = useState(false)
  const [prompts, setPrompts] = useState<Record<string, string>>({})
  const [promptDefaults, setPromptDefaults] = useState<Record<string, string>>({})
  const [promptMeta, setPromptMeta] = useState<{ key: string; title: string; description?: string }[]>([])
  const [activePromptKey, setActivePromptKey] = useState('analyze')

  const selectedProvider = providers.find((p) => p.id === providerId)
  const isCustom = providerId === 'custom'
  const showBaseUrl = isCustom || Boolean(selectedProvider?.requires_base_url)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [config, providerList] = await Promise.all([
          apiClient.getAiConfig(),
          apiClient.listAiProviders(),
        ])
        if (cancelled) return
        setProviders(providerList.providers)
        applyConfig(config)
      } catch {
        if (!cancelled) setSaveError('加载 AI 配置失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  const applyConfig = (config: AIConfigResponse) => {
    setProviderId(config.provider_id)
    setDisplayName(config.display_name)
    setBaseUrl(config.base_url || '')
    setModel(config.model)
    setApiKeySet(config.api_key_set)
    setEnabled(config.enabled)
    setApiKey('')
    setPrompts((config.prompts as Record<string, string>) || {})
    setPromptDefaults(config.prompt_defaults || {})
    const meta = config.prompt_meta || []
    setPromptMeta(meta)
    if (meta.length > 0) setActivePromptKey(meta[0].key)
  }

  const handleProviderChange = (id: string) => {
    setProviderId(id)
    const preset = providers.find((p) => p.id === id)
    if (preset) {
      setDisplayName(preset.name)
      setBaseUrl(preset.default_base_url || '')
    }
    setModels([])
    setModelsError('')
  }

  const handleLoadModels = async () => {
    setModelsLoading(true)
    setModelsError('')
    try {
      const result = await apiClient.listAiModels({
        provider_id: providerId,
        api_key: apiKey.trim() || undefined,
        base_url: baseUrl.trim() || undefined,
      })
      setModels(result.models)
      if (result.models.length > 0 && !result.models.some((m) => m.id === model)) {
        setModel(result.models[0].id)
      }
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setModelsError(formatDetail(detail) || '加载模型列表失败')
      setModels([])
    } finally {
      setModelsLoading(false)
    }
  }

  const handleSave = async () => {
    setSaveError('')
    try {
      const config = await apiClient.updateAiConfig({
        provider_id: providerId,
        display_name: isCustom ? displayName : undefined,
        base_url: showBaseUrl ? baseUrl.trim() || undefined : undefined,
        model,
        api_key: apiKey.trim() || undefined,
        enabled,
        prompts,
      })
      applyConfig(config)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setSaveError(formatDetail(detail) || '保存失败')
    }
  }

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6 text-center text-gray-500">
        加载中...
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-1">AI设置</h3>
      <p className="text-sm text-gray-500 mb-6">
        配置租户级 AI 服务，用于告警根因分析、内容润色等功能。API Key 加密存储在服务端。
      </p>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">AI提供商</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {providers.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => handleProviderChange(p.id)}
                className={`p-4 border rounded-xl flex flex-col items-center gap-1 transition-all text-center ${
                  providerId === p.id ? 'border-blue-500 bg-blue-50' : 'hover:border-gray-300'
                }`}
              >
                <span className="font-medium text-sm">{p.name}</span>
                {p.description && (
                  <span className="text-xs text-gray-500 line-clamp-2">{p.description}</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {isCustom && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">显示名称</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="例如：公司自建网关"
            />
          </div>
        )}

        {showBaseUrl && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              API Base URL {isCustom && <span className="text-red-500">*</span>}
            </label>
            <input
              type="url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="https://api.example.com/v1"
            />
            <p className="text-xs text-gray-500 mt-1">OpenAI 兼容接口根路径，需包含 /v1</p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder={apiKeySet ? '已保存，留空则不修改' : '输入 API Key'}
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-gray-700">模型</label>
            <button
              type="button"
              onClick={handleLoadModels}
              disabled={modelsLoading}
              className="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
            >
              {modelsLoading ? '加载中...' : '验证并加载模型'}
            </button>
          </div>
          {modelsError && <p className="text-sm text-red-600 mb-2">{modelsError}</p>}
          {models.length > 0 ? (
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>{m.name || m.id}</option>
              ))}
            </select>
          ) : (
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="先加载模型列表，或直接输入模型 ID"
            />
          )}
        </div>

        <div className="flex items-center gap-2">
          <input
            id="ai-enabled"
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <label htmlFor="ai-enabled" className="text-sm text-gray-700">
            启用 AI 功能（告警详情页可使用根因分析等）
          </label>
        </div>

        {promptMeta.length > 0 && (
          <div className="pt-6 border-t">
            <h4 className="text-sm font-semibold text-gray-800 mb-1">提示词（System Prompt）</h4>
            <p className="text-xs text-gray-500 mb-4">
              自定义各 AI 模块的系统提示词。告警字段仍由系统自动注入；润色模块可使用占位符
              <code className="mx-1 px-1 bg-gray-100 rounded">{'{style_instruction}'}</code>
            </p>
            <div className="flex flex-wrap gap-2 mb-3">
              {promptMeta.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => setActivePromptKey(m.key)}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                    activePromptKey === m.key
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 hover:border-gray-300 text-gray-700'
                  }`}
                >
                  {m.title}
                </button>
              ))}
            </div>
            {(() => {
              const meta = promptMeta.find((m) => m.key === activePromptKey)
              return (
                <div className="border rounded-lg p-4 bg-gray-50/50">
                  {meta?.description && (
                    <p className="text-xs text-gray-500 mb-2">{meta.description}</p>
                  )}
                  <textarea
                    value={prompts[activePromptKey] ?? ''}
                    onChange={(e) =>
                      setPrompts((prev) => ({ ...prev, [activePromptKey]: e.target.value }))
                    }
                    rows={14}
                    className="w-full px-3 py-2 border rounded-lg font-mono text-xs leading-relaxed focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white"
                    spellCheck={false}
                  />
                  <div className="flex justify-end mt-2">
                    <button
                      type="button"
                      onClick={() =>
                        setPrompts((prev) => ({
                          ...prev,
                          [activePromptKey]: promptDefaults[activePromptKey] || '',
                        }))
                      }
                      className="text-sm text-gray-600 hover:text-blue-600"
                    >
                      恢复该模块默认提示词
                    </button>
                  </div>
                </div>
              )
            })()}
          </div>
        )}

        <div className="flex items-center gap-4 pt-4 border-t">
          <button
            type="button"
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            保存配置
          </button>
          {saved && <span className="text-sm text-green-600">配置已保存</span>}
          {saveError && <span className="text-sm text-red-600">{saveError}</span>}
        </div>
      </div>

      <div className="mt-8 pt-6 border-t">
        <h4 className="text-sm font-medium mb-4">AI功能说明</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="font-medium mb-1">🔍 根因分析</div>
            <div className="text-sm text-gray-600">自动分析告警发生的可能原因</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="font-medium mb-1">✨ 内容润色</div>
            <div className="text-sm text-gray-600">将告警内容润色成更易读格式</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: string }).msg)
        return JSON.stringify(item)
      })
      .join('; ')
  }
  return ''
}
