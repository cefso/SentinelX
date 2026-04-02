import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'

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

const CHANNEL_TYPES = [
  { value: 'dingtalk', label: '钉钉', icon: '🔔' },
  { value: 'feishu', label: '飞书', icon: '✈️' },
  { value: 'wecom', label: '企业微信', icon: '💬' },
  { value: 'email', label: '邮件', icon: '📧' },
  { value: 'webhook', label: 'Webhook', icon: '🔗' },
  { value: 'slack', label: 'Slack', icon: '💬' },
]

export function ChannelsPage() {
  const queryClient = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null)
  const [filter, setFilter] = useState<string>('all')

  const { data: channels = [], isLoading } = useQuery<Channel[]>({
    queryKey: ['channels'],
    queryFn: () => apiClient.get('/channels'),
  })

  const filteredChannels = filter === 'all'
    ? channels
    : channels.filter(c => c.channel_type === filter)

  const deleteMutation = useMutation({
    mutationFn: (channelId: number) => apiClient.delete(`/channels/${channelId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['channels'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ channelId, is_active }: { channelId: number; is_active: boolean }) =>
      apiClient.put(`/channels/${channelId}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['channels'] }),
  })

  const handleEdit = (channel: Channel) => {
    setEditingChannel(channel)
    setShowModal(true)
  }

  const handleCreate = () => {
    setEditingChannel(null)
    setShowModal(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">通知渠道</h1>
          <p className="text-gray-600">管理钉钉、飞书、企业微信等通知渠道</p>
        </div>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
        >
          创建渠道
        </button>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded ${filter === 'all' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100'}`}
        >
          全部 ({channels.length})
        </button>
        {CHANNEL_TYPES.map((type) => {
          const count = channels.filter(c => c.channel_type === type.value).length
          return (
            <button
              key={type.value}
              onClick={() => setFilter(type.value)}
              className={`px-3 py-1 rounded ${filter === type.value ? 'bg-blue-100 text-blue-700' : 'bg-gray-100'}`}
            >
              {type.icon} {type.label} ({count})
            </button>
          )
        })}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading ? (
          <div className="col-span-full p-8 text-center">加载中...</div>
        ) : filteredChannels.length === 0 ? (
          <div className="col-span-full p-8 text-center text-gray-500">暂无渠道</div>
        ) : (
          filteredChannels.map((channel) => {
            const typeInfo = CHANNEL_TYPES.find(t => t.value === channel.channel_type)
            return (
              <div key={channel.id} className="bg-white rounded-lg shadow p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{typeInfo?.icon || '📢'}</span>
                    <div>
                      <div className="font-medium">{channel.name}</div>
                      <div className="text-sm text-gray-500">{channel.code}</div>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleEdit(channel)}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      编辑
                    </button>
                    <button
                      onClick={() => {
                        if (confirm('确定要删除该渠道吗？')) {
                          deleteMutation.mutate(channel.id)
                        }
                      }}
                      disabled={deleteMutation.isPending}
                      className="text-red-600 hover:text-red-800 text-sm disabled:opacity-50"
                    >
                      删除
                    </button>
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">类型</span>
                    <span>{typeInfo?.label || channel.channel_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">状态</span>
                    <button
                      onClick={() => toggleMutation.mutate({ channelId: channel.id, is_active: !channel.is_active })}
                      disabled={toggleMutation.isPending}
                      className={`px-2 py-0.5 text-xs rounded disabled:opacity-50 ${channel.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}
                    >
                      {channel.is_active ? '启用' : '停用'}
                    </button>
                  </div>
                  {channel.is_default && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">默认</span>
                      <span className="text-blue-600">是</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-gray-500">发送统计</span>
                    <span>
                      <span className="text-green-600">{channel.success_count}</span>
                      {' / '}
                      <span className="text-red-600">{channel.fail_count}</span>
                      {' / '}
                      <span>{channel.send_count}</span>
                    </span>
                  </div>
                  {channel.last_send_at && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">最后发送</span>
                      <span className="text-xs">{new Date(channel.last_send_at).toLocaleString('zh-CN')}</span>
                    </div>
                  )}
                </div>

                {channel.config && Object.keys(channel.config).length > 0 && (
                  <div className="mt-3 pt-3 border-t">
                    <div className="text-xs text-gray-500 mb-1">配置信息</div>
                    <div className="text-xs space-y-1">
                      {channel.config.webhook_url && (
                        <div className="truncate text-gray-600">URL: {channel.config.webhook_url}</div>
                      )}
                      {channel.config.recipients && (
                        <div className="text-gray-600"> recipients: {channel.config.recipients}</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {showModal && (
        <ChannelModal
          channel={editingChannel}
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            queryClient.invalidateQueries({ queryKey: ['channels'] })
          }}
        />
      )}
    </div>
  )
}

function ChannelModal({ channel, onClose, onSuccess }: { channel: Channel | null; onClose: () => void; onSuccess: () => void }) {
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
    if (channel) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
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
          <div className="grid grid-cols-2 gap-4">
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
              <label className="block text-sm font-medium text-gray-700 mb-1">渠道代码</label>
              <input
                type="text"
                required
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
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
            <>
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
            </>
          )}

          {formData.channel_type === 'wecom' && (
            <>
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
            </>
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