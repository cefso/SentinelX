import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { ChannelModal, CHANNEL_TYPES } from './ChannelModal'
import { Modal } from '@/components/common/Modal'
import { FilterTabs } from '@/components/common/FilterTabs'
import { Pagination } from '@/components/common/Pagination'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

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

interface TestResult {
  success: boolean
  error?: string
  response_data?: Record<string, any>
}

interface NotificationRecord {
  id: number
  alert_id: number
  channel_id: number
  channel_type: string
  status: string
  error_message?: string
  retry_count: number
  created_at: string
}

export function ChannelsPage() {
  const queryClient = useQueryClient()
  const { currentTenant, user } = useAuthStore()
  const [showModal, setShowModal] = useState(false)
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null)
  const [filter, setFilter] = useState<string>('all')
  const [activeTab, setActiveTab] = useState<'channels' | 'records'>('channels')
  const [showTestModal, setShowTestModal] = useState(false)
  const [testChannel, setTestChannel] = useState<Channel | null>(null)
  const [testContent, setTestContent] = useState('')
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [recordFilter, setRecordFilter] = useState<string>('all')
  const [recordPage, setRecordPage] = useState(0)

  // 权限检查
  const permissions = currentTenant?.permissions || []
  const canWrite = permissions.includes('*') || permissions.includes('channels:write') || user?.is_system === true
  const canTest = permissions.includes('*') || permissions.includes('channels:test') || user?.is_system === true

  const { data: channels = [], isLoading } = useQuery<Channel[]>({
    queryKey: ['channels'],
    queryFn: () => apiClient.get('/channels'),
  })

  const { data: notificationRecords, isLoading: recordsLoading } = useQuery<{
    items: NotificationRecord[]
    total: number
    limit: number
    offset: number
  }>({
    queryKey: ['notification-records', recordFilter, recordPage],
    queryFn: () => apiClient.get('/notifications', {
      channel_type: recordFilter === 'all' ? undefined : recordFilter,
      limit: 20,
      offset: recordPage * 20,
    }),
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

  const testMutation = useMutation({
    mutationFn: ({ channelId, content }: { channelId: number; content?: string }) =>
      apiClient.post<TestResult>(`/channels/${channelId}/test`, content ? { content } : {}),
    onSuccess: (result) => setTestResult(result),
    onError: (err: any) => setTestResult({ success: false, error: err.response?.data?.detail || '请求失败' }),
  })

  const handleEdit = (channel: Channel) => {
    setEditingChannel(channel)
    setShowModal(true)
  }

  const handleCreate = () => {
    setEditingChannel(null)
    setShowModal(true)
  }

  const handleOpenTest = (channel: Channel) => {
    setTestChannel(channel)
    setShowTestModal(true)
    setTestContent('')
    setTestResult(null)
  }

  const renderRecordsContent = () => {
    if (recordsLoading) {
      return <div className="p-8 text-center text-muted-foreground">加载中...</div>
    }
    if (!notificationRecords || notificationRecords.items.length === 0) {
      return <div className="p-8 text-center text-muted-foreground">暂无通知记录</div>
    }
    return (
      <div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">时间</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">渠道</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">告警ID</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">状态</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">错误信息</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">重试</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {notificationRecords.items.map((record) => {
                const typeInfo = CHANNEL_TYPES.find(t => t.value === record.channel_type)
                const statusStyle = record.status === 'sent'
                  ? 'bg-green-100 text-green-800'
                  : record.status === 'failed'
                  ? 'bg-destructive/10 text-destructive'
                  : record.status === 'pending'
                  ? 'bg-yellow-100 text-yellow-800'
                  : 'bg-secondary text-secondary-foreground'
                const statusLabel = record.status === 'sent' ? '已发送'
                  : record.status === 'failed' ? '失败'
                  : record.status === 'pending' ? '待发送'
                  : record.status
                return (
                  <tr key={record.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {new Date(record.created_at).toLocaleString('zh-CN')}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm">
                        {typeInfo?.icon} {typeInfo?.label || record.channel_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-primary">#{record.alert_id}</td>
                    <td className="px-4 py-3">
                      <span className={cn("px-2 py-0.5 text-xs rounded", statusStyle)}>
                        {statusLabel}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-destructive max-w-xs truncate">
                      {record.error_message || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {record.retry_count} 次
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        <div className="p-4 border-t">
          <Pagination
            page={recordPage + 1}
            totalPages={Math.ceil(notificationRecords.total / 20)}
            total={notificationRecords.total}
            onPageChange={(p) => setRecordPage(p - 1)}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">通知渠道</h1>
          <p className="text-sm text-muted-foreground mt-0.5">管理钉钉、飞书、企业微信等通知渠道</p>
        </div>
        {canWrite && (
          <Button onClick={handleCreate}>创建渠道</Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        <FilterTabs
          tabs={[
            { key: 'channels', label: `渠道管理 (${channels.length})` },
            { key: 'records', label: `通知记录 (${notificationRecords?.total || 0})` },
          ]}
          active={activeTab}
          onChange={(k) => setActiveTab(k as 'channels' | 'records')}
        />
      </div>

      {activeTab === 'channels' ? (
        <div className="space-y-4">
          {/* Channel type filter */}
          <FilterTabs
            tabs={[
              { key: 'all', label: `全部 (${channels.length})` },
              ...CHANNEL_TYPES.map((type) => ({
                key: type.value,
                label: `${type.icon} ${type.label}`,
                count: channels.filter(c => c.channel_type === type.value).length,
              })),
            ]}
            active={filter}
            onChange={setFilter}
          />

          {/* Channel grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {isLoading ? (
              <div className="col-span-full p-8 text-center text-muted-foreground">加载中...</div>
            ) : filteredChannels.length === 0 ? (
              <div className="col-span-full p-8 text-center text-muted-foreground">暂无渠道</div>
            ) : (
              filteredChannels.map((channel) => {
                const typeInfo = CHANNEL_TYPES.find(t => t.value === channel.channel_type)
                return (
                  <div key={channel.id} className="bg-card rounded-lg border shadow-sm p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="text-2xl">{typeInfo?.icon || '📢'}</span>
                        <div>
                          <div className="font-medium">{channel.name}</div>
                          <div className="text-sm text-muted-foreground">{channel.code}</div>
                        </div>
                      </div>
                      {(canTest || canWrite) && (
                        <div className="flex gap-1">
                          {canTest && (
                            <button
                              onClick={() => handleOpenTest(channel)}
                              disabled={!channel.is_active}
                              className="text-green-600 hover:text-green-800 text-sm disabled:opacity-30"
                              title={channel.is_active ? '发送测试消息' : '请先启用渠道'}
                            >
                              测试
                            </button>
                          )}
                          {canWrite && (
                            <button
                              onClick={() => handleEdit(channel)}
                              className="text-primary hover:text-primary/80 text-sm"
                            >
                              编辑
                            </button>
                          )}
                          {canWrite && (
                            <button
                              onClick={() => {
                                if (confirm('确定要删除该渠道吗？')) {
                                  deleteMutation.mutate(channel.id)
                                }
                              }}
                              disabled={deleteMutation.isPending}
                              className="text-destructive hover:text-destructive/80 text-sm disabled:opacity-50"
                            >
                              删除
                            </button>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">类型</span>
                        <span>{typeInfo?.label || channel.channel_type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">状态</span>
                        {canWrite ? (
                          <button
                            onClick={() => toggleMutation.mutate({ channelId: channel.id, is_active: !channel.is_active })}
                            disabled={toggleMutation.isPending}
                            className={cn(
                              "px-2 py-0.5 text-xs rounded transition-colors disabled:opacity-50",
                              channel.is_active 
                                ? "bg-green-100 text-green-800 hover:bg-green-200" 
                                : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                            )}
                          >
                            {channel.is_active ? '启用' : '停用'}
                          </button>
                        ) : (
                          <span className={cn(
                            "px-2 py-0.5 text-xs rounded",
                            channel.is_active ? "bg-green-100 text-green-800" : "bg-secondary text-secondary-foreground"
                          )}>
                            {channel.is_active ? '已启用' : '已停用'}
                          </span>
                        )}
                      </div>
                      {channel.is_default && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">默认</span>
                          <span className="text-primary">是</span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">发送统计</span>
                        <span>
                          <span className="text-green-600">{channel.success_count}</span>
                          {' / '}
                          <span className="text-destructive">{channel.fail_count}</span>
                          {' / '}
                          <span>{channel.send_count}</span>
                        </span>
                      </div>
                      {channel.last_send_at && (
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">最后发送</span>
                          <span className="text-xs">{new Date(channel.last_send_at).toLocaleString('zh-CN')}</span>
                        </div>
                      )}
                    </div>

                    {channel.config && Object.keys(channel.config).length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border">
                        <div className="text-xs text-muted-foreground mb-1">配置信息</div>
                        <div className="text-xs space-y-1">
                          {channel.config.webhook_url && (
                            <div className="truncate text-muted-foreground">URL: {channel.config.webhook_url}</div>
                          )}
                          {channel.config.recipients && (
                            <div className="text-muted-foreground"> recipients: {channel.config.recipients}</div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Records filter */}
          <FilterTabs
            tabs={[
              { key: 'all', label: '全部' },
              ...CHANNEL_TYPES.map((type) => ({
                key: type.value,
                label: `${type.icon} ${type.label}`,
              })),
            ]}
            active={recordFilter}
            onChange={(k) => { setRecordFilter(k); setRecordPage(0) }}
          />

          {/* Records table */}
          <div className="bg-card rounded-lg border shadow-sm">
            {renderRecordsContent()}
          </div>
        </div>
      )}

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

      {showTestModal && testChannel && (
        <Modal
          open={showTestModal}
          onOpenChange={(open) => {
            if (!open) {
              setShowTestModal(false)
              setTestChannel(null)
              setTestContent('')
              setTestResult(null)
            }
          }}
          title={`测试发送 - ${testChannel.name}`}
          description={`渠道类型: ${testChannel.channel_type}`}
          size="md"
          footer={
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setShowTestModal(false)
                  setTestChannel(null)
                  setTestContent('')
                  setTestResult(null)
                }}
              >
                关闭
              </Button>
              <Button
                onClick={() => testMutation.mutate({ channelId: testChannel.id, content: testContent })}
                disabled={testMutation.isPending}
                className="flex items-center gap-2"
              >
                {testMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                {testMutation.isPending ? '发送中...' : '发送测试消息'}
              </Button>
            </>
          }
        >
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>测试消息内容 (可选)</Label>
              <Textarea
                value={testContent}
                onChange={(e) => setTestContent(e.target.value)}
                placeholder="留空将使用默认测试内容"
                rows={3}
              />
            </div>

            {testResult && (
              <div className={cn("p-3 rounded-lg", testResult.success ? 'bg-green-50' : 'bg-destructive/10')}>
                <div className="flex items-center gap-2">
                  {testResult.success ? (
                    <CheckCircle className="w-5 h-5 text-green-600 shrink-0" />
                  ) : (
                    <XCircle className="w-5 h-5 text-destructive shrink-0" />
                  )}
                  <span className={cn("font-medium", testResult.success ? 'text-green-700' : 'text-destructive')}>
                    {testResult.success ? '发送成功' : '发送失败'}
                  </span>
                </div>
                {testResult.error && (
                  <p className="text-sm text-destructive mt-1 ml-7">{testResult.error}</p>
                )}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}
