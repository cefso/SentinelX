import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { generateCode } from '@/utils/code'
import { Modal } from '@/components/common/Modal'
import { channelSchema, type ChannelFormData } from '@/schemas'

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
  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<ChannelFormData>({
    resolver: zodResolver(channelSchema),
    defaultValues: {
      name: channel?.name || '',
      channel_type: channel?.channel_type || 'dingtalk',
      config: channel?.config || {},
      is_active: channel?.is_active ?? true,
      is_default: channel?.is_default ?? false,
    },
  })

  const channelType = watch('channel_type')
  const config = watch('config')

  const updateConfig = (key: string, value: string) => {
    setValue('config', { ...config, [key]: value })
  }

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/channels', data),
    onSuccess,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/channels/${channel?.id}`, data),
    onSuccess,
  })

  const onSubmit = (data: ChannelFormData) => {
    const submitData = {
      ...data,
      code: channel ? channel.code : generateCode(data.name),
    }
    if (channel) {
      updateMutation.mutate(submitData)
    } else {
      createMutation.mutate(submitData)
    }
  }

  return (
    <Modal
      open={true}
      onOpenChange={(open) => { if (!open) onClose() }}
      title={channel ? '编辑渠道' : '创建渠道'}
      size="lg"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">渠道名称</label>
            <input
              type="text"
              {...register('name')}
              className="w-full px-3 py-2 border rounded-md"
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-500">{errors.name.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">渠道类型</label>
            <Controller
              name="channel_type"
              control={control}
              render={({ field }) => (
                <div className="grid grid-cols-3 gap-2">
                  {CHANNEL_TYPES.map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => field.onChange(type.value)}
                      className={`p-2 border rounded flex items-center gap-2 ${field.value === type.value ? 'border-blue-500 bg-blue-50' : ''}`}
                    >
                      <span>{type.icon}</span>
                      <span className="text-sm">{type.label}</span>
                    </button>
                  ))}
                </div>
              )}
            />
            {errors.channel_type && (
              <p className="mt-1 text-sm text-red-500">{errors.channel_type.message}</p>
            )}
          </div>

          {channelType === 'dingtalk' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
                <input
                  type="url"
                  value={config?.webhook_url || ''}
                  onChange={(e) => updateConfig('webhook_url', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="https://oapi.dingtalk.com/robot/send?access_token=xxx"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Secret (可选)</label>
                <input
                  type="text"
                  value={config?.secret || ''}
                  onChange={(e) => updateConfig('secret', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="加签密钥"
                />
              </div>
            </>
          )}

          {channelType === 'feishu' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={config?.webhook_url || ''}
                onChange={(e) => updateConfig('webhook_url', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
              />
            </div>
          )}

          {channelType === 'wecom' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={config?.webhook_url || ''}
                onChange={(e) => updateConfig('webhook_url', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
              />
            </div>
          )}

          {channelType === 'email' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">SMTP 服务器</label>
                <input
                  type="text"
                  value={config?.smtp_host || ''}
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
                    value={config?.smtp_port || 587}
                    onChange={(e) => updateConfig('smtp_port', e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">发件人</label>
                  <input
                    type="email"
                    value={config?.from_addr || ''}
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
                    value={config?.username || ''}
                    onChange={(e) => updateConfig('username', e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
                  <input
                    type="password"
                    value={config?.password || ''}
                    onChange={(e) => updateConfig('password', e.target.value)}
                    className="w-full px-3 py-2 border rounded-md"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">收件人 (逗号分隔)</label>
                <input
                  type="text"
                  value={config?.recipients || ''}
                  onChange={(e) => updateConfig('recipients', e.target.value)}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="user1@example.com, user2@example.com"
                />
              </div>
            </>
          )}

          {channelType === 'webhook' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={config?.webhook_url || ''}
                onChange={(e) => updateConfig('webhook_url', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://example.com/webhook"
              />
            </div>
          )}

          {channelType === 'slack' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <input
                type="url"
                value={config?.webhook_url || ''}
                onChange={(e) => updateConfig('webhook_url', e.target.value)}
                className="w-full px-3 py-2 border rounded-md"
                placeholder="https://hooks.slack.com/services/..."
              />
            </div>
          )}

          <div className="flex items-center gap-4">
            <Controller
              name="is_active"
              control={control}
              render={({ field }) => (
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={field.value}
                    onChange={field.onChange}
                    className="rounded"
                  />
                  <span className="text-sm">启用</span>
                </label>
              )}
            />
            <Controller
              name="is_default"
              control={control}
              render={({ field }) => (
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={field.value}
                    onChange={field.onChange}
                    className="rounded"
                  />
                  <span className="text-sm">默认渠道</span>
                </label>
              )}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <button type="button" onClick={onClose} className="px-4 py-2 border rounded-md hover:bg-gray-50">
              取消
            </button>
            <button
              type="submit"
              disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
            >
              {channel ? '保存' : '创建'}
            </button>
          </div>
        </form>
    </Modal>
  )
}
