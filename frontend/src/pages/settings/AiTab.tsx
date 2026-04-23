import { useState } from 'react'

export function AISettingsTab() {
  const [provider, setProvider] = useState('openai')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState('gpt-4')
  const [saved, setSaved] = useState(false)

  const providers = [
    { value: 'openai', label: 'OpenAI', models: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'] },
    { value: 'anthropic', label: 'Anthropic Claude', models: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'] },
    { value: 'qwen', label: '阿里云 Qwen', models: ['qwen-max', 'qwen-plus', 'qwen-turbo'] },
  ]

  const handleSave = () => {
    localStorage.setItem('ai_config', JSON.stringify({ provider, apiKey, model }))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-1">AI设置</h3>
      <p className="text-sm text-gray-500 mb-6">
        配置AI服务提供商，用于根因分析、内容润色等功能。API Key 仅存储在本地浏览器中。
      </p>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">AI提供商</label>
          <div className="grid grid-cols-3 gap-3">
            {providers.map((p) => (
              <button
                key={p.value}
                onClick={() => { setProvider(p.value); setModel(p.models[0]); }}
                className={`p-4 border rounded-xl flex flex-col items-center gap-2 transition-all ${
                  provider === p.value ? 'border-blue-500 bg-blue-50' : 'hover:border-gray-300'
                }`}
              >
                <span className="font-medium">{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="输入API Key"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">模型</label>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {providers.find(p => p.value === provider)?.models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-4 pt-4 border-t">
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            保存配置
          </button>
          {saved && <span className="text-sm text-green-600">配置已保存</span>}
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
