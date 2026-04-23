import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { generateCode } from '@/utils/code'

interface Channel {
  id: number
  name: string
  code: string
  channel_type: string
  config: Record<string, any>
  is_active: boolean
  is_default: boolean
  send_count: number
  success_count: number
  fail_count: number
  last_send_at?: string
  created_at: string
}

export const CHANNEL_TYPES = [
  { value: 'dingtalk', label: '钉钉', icon: '🔔' },
  { value: 'feishu', label: '飞书', icon: '✈️' },
  { value: 'wecom', label: '企业微信', icon: '💬' },
  { value: 'email', label: '邮件', icon: '📧' },
  { value: 'webhook', label: 'Webhook', icon: '🔗' },
  { value: 'slack', label: 'Slack', icon: '💬' },
]

export function ChannelModal({ channel, onClose, onSuccess }: { channel: Channel | null; onClose: () => void; onSuccess: () => void }) {
  const [formData, setFormData] = useState({
    name: channel?.name || '',
    code: channel?.code || '',
    channel_type: channel?.channel_type || 'dingtalk',
    config: channel?.config || {},
    is_active: channel?.is_active ?? true,
    is_default: channel?.is_default ?? false,
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/channels', data),
    onSuccess,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/channels/${channel?.id}`, data),
    onSuccess,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data = {
      ...formData,
      code: channel ? formData.code : generateCode(formData.name),
    }
    if (channel) {
      updateMutation.mutate(data)
    } else {
      createMutation.mutate(data)
    }
  }

  const updateConfig = (key: string, value: string) => {
    setFormData({
      ...formData,
      config: { ...formData.config, [key]: value },
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg w-full max-w-lg max-h-[90vh] overflow-auto">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold">{channel ? '编辑渠道' : '创建渠道'}</h2>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">渠道名称</label>
            <input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">渠道类型</label>
            <div className="grid grid-cols-3 gap-2">
              {CHANNEL_TYPES.map((type) => (
                <button
                  key={type.value}
                  type="button"
                  onClick={() => setFormData({ ...formData, channel_type: type.value })}
                  className={`p-2 border rounded flex items-center gap-2 ${formData.channel_type === type.value ? 'border-blue-500 bg-blue-50' : ''}`}
                >
                  <span>{type.icon}</span>
                  <span className="text-sm">{type.label}</span>
                </button>
              ))}
            </div>
          </div>

          {formData.channel_type === 'dingtalk' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
                <input
                  type="url"
                  value={formData.config.webhook_url || ''}
                  onChange={(e) => updateConfig('webhook_url', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Secret (可选)</label>
                <input
                  type="text"
                  value={formData.config.secret || ''}
                  onChange={(e) => updateConfig('secret', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="加签密钥"
                />
              </div>
            </>
          )}

          {formData.channel_type === 'feishu' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={formData.config.webhook_url || ''}
                onChange={(e) => updateConfig('webhook_url', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
              />
            </div>
          )}

          {formData.channel_type === 'wecom' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={formData.config.webhook_url || ''}
                onChange={(e) => updateConfig('webhook_url', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
              />
            </div>
          )}

          {formData.channel_type === 'email' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SMTP 服务器</label>
                <input
                  type="text"
                  value={formData.config.smtp_host || ''}
                  onChange={(e) => updateConfig('smtp_host', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="smtp.example.com"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SMTP 端口</label>
                  <input
                    type="number"
                    value={formData.config.smtp_port || 587}
                    onChange={(e) => updateConfig('smtp_port', e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">发件人</label>
                  <input
                    type="email"
                    value={formData.config.from_addr || ''}
                    onChange={(e) => updateConfig('from_addr', e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
                  <input
                    type="text"
                    value={formData.config.username || ''}
                    onChange={(e) => updateConfig('username', e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
                  <input
                    type="password"
                    value={formData.config.password || ''}
                    onChange={(e) => updateConfig('password', e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">收件人 (逗号分隔)</label>
                <input
                  type="text"
                  value={formData.config.recipients || ''}
                  onChange={(e) => updateConfig('recipients', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="user1@example.com, user2@example.com"
                />
              </div>
            </>
          )}

          {formData.channel_type === 'webhook' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                required
                value={formData.config.webhook_url || ''}
                onChange={(e) => updateConfig('webhook_url', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://example.com/webhook"
              />
            </div>
          )}

          {formData.channel_type === 'slack' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                required
                value={formData.config.webhook_url || ''}
                onChange={(e) => updateConfig('webhook_url', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://hooks.slack.com/services/..."
              />
            </div>
          )}

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm">启用</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_default}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                className="rounded"
              />
              <span className="text-sm">默认渠道</span>
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {channel ? '保存' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
