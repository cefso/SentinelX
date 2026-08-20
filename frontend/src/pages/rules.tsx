import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { ConditionEditor, Condition } from '@/components/condition/ConditionEditor'
import { FIELD_CONFIGS } from '@/components/condition/constants'
import { generateCode } from '@/utils/code'
import { RulesLayout } from '@/components/rules/RulesLayout'
import { FilterTabs } from '@/components/common/FilterTabs'
import { HelpCircle, Zap } from 'lucide-react'
import { NotificationTemplate } from './templates'
import { Modal } from '@/components/common/Modal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

export type { Condition }

interface Rule {
  id: number
  name: string
  code: string
  description?: string
  conditions: Condition[]
  condition_mode: string
  actions: (string | { channel_id: number; template_id?: number })[]
  priority: number
  is_active: boolean
  suppress_config?: any
  aggregate_config?: any
  deduplication_config?: any
  match_count: number
  last_match_at?: string
  created_at: string
  updated_at: string
}

export function RulesPage() {
  const queryClient = useQueryClient()
  const { currentTenant, user } = useAuthStore()
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<Rule | null>(null)
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all')

  // 权限检查
  const permissions = currentTenant?.permissions || []
  const canWrite = permissions.includes('*') || permissions.includes('rules:write') || user?.is_system === true

  const { data: rules = [], isLoading } = useQuery<Rule[]>({
    queryKey: ['rules', filter],
    queryFn: () => {
      const params = filter === 'active' ? { is_active: true } : filter === 'inactive' ? { is_active: false } : {}
      return apiClient.get('/rules', params)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (ruleId: number) => apiClient.delete(`/rules/${ruleId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules'] }),
  })

  const toggleMutation = useMutation({
    mutationFn: ({ ruleId, is_active }: { ruleId: number; is_active: boolean }) =>
      apiClient.put(`/rules/${ruleId}`, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rules'] }),
  })

  const handleEdit = (rule: Rule) => {
    setEditingRule(rule)
    setShowModal(true)
  }

  const handleCreate = () => {
    setEditingRule(null)
    setShowModal(true)
  }

  return (
    <RulesLayout>
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          路由规则决定告警匹配后发送到哪些通知渠道
        </p>
        {canWrite && (
          <Button onClick={handleCreate}>
            创建路由规则
          </Button>
        )}
      </div>

      <FilterTabs
        tabs={[
          { key: 'all', label: '全部', count: rules.length },
          { key: 'active', label: '启用中' },
          { key: 'inactive', label: '停用中' },
        ]}
        active={filter}
        onChange={(k) => setFilter(k as 'all' | 'active' | 'inactive')}
      />

      <div className="bg-card rounded-lg border shadow-sm">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">加载中...</div>
        ) : rules.length === 0 ? (
          <div className="p-12 text-center">
            <Zap className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
            <div className="text-muted-foreground font-medium">暂无路由规则</div>
            <div className="text-sm text-muted-foreground/70 mt-1">创建路由规则将告警发送到指定通知渠道</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">规则名称</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">条件</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">优先级</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">匹配次数</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">状态</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3">
                      <div className="font-medium">{rule.name}</div>
                      <div className="text-sm text-muted-foreground">{rule.code}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm">
                        {rule.conditions.length} 个条件 ({rule.condition_mode})
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {rule.conditions.slice(0, 2).map((c, i) => {
                          const fc = FIELD_CONFIGS.find(f => f.value === c.field)
                          return (
                            <span key={i} className="mr-1">
                              {fc?.label || c.field} {c.operator} {String(c.value)}
                            </span>
                          )
                        })}
                        {rule.conditions.length > 2 && '...'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 text-sm bg-primary/10 text-primary rounded">
                        {rule.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm">{rule.match_count}</div>
                      {rule.last_match_at && (
                        <div className="text-xs text-muted-foreground">
                          {new Date(rule.last_match_at).toLocaleDateString('zh-CN')}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {canWrite ? (
                        <button
                          onClick={() => toggleMutation.mutate({ ruleId: rule.id, is_active: !rule.is_active })}
                          disabled={toggleMutation.isPending}
                          className={cn(
                            "px-2 py-1 text-xs rounded transition-colors disabled:opacity-50",
                            rule.is_active 
                              ? "bg-green-100 text-green-800 hover:bg-green-200" 
                              : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                          )}
                        >
                          {rule.is_active ? '启用' : '停用'}
                        </button>
                      ) : (
                        <span className={cn(
                          "px-2 py-1 text-xs rounded",
                          rule.is_active ? "bg-green-100 text-green-800" : "bg-secondary text-secondary-foreground"
                        )}>
                          {rule.is_active ? '已启用' : '已停用'}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {canWrite && (
                        <>
                          <button
                            onClick={() => handleEdit(rule)}
                            className="text-primary hover:text-primary/80 mr-3"
                          >
                            编辑
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('确定要删除该规则吗？')) {
                                deleteMutation.mutate(rule.id)
                              }
                            }}
                            disabled={deleteMutation.isPending}
                            className="text-destructive hover:text-destructive/80 disabled:opacity-50"
                          >
                            删除
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showModal && (
        <RuleModal
          rule={editingRule}
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            queryClient.invalidateQueries({ queryKey: ['rules'] })
          }}
          initialConditions={[]}
        />
      )}
    </RulesLayout>
  )
}

export function RuleModal({ rule, onClose, onSuccess, initialConditions, showModal: _showModal }: { rule: Rule | null; onClose: () => void; onSuccess: () => void; initialConditions?: Condition[]; showModal?: boolean }) {
  // Channel -> template mapping: { channelId: templateId | null }
  const [channelTemplateMap, setChannelTemplateMap] = useState<Record<number, number | null>>(() => {
    // Initialize from existing rule actions (new format)
    const map: Record<number, number | null> = {}
    const actions = rule?.actions || []
    for (const action of actions) {
      if (typeof action === 'object' && action !== null) {
        map[action.channel_id] = action.template_id ?? null
      }
    }
    return map
  })

  const [formData, setFormData] = useState({
    name: rule?.name || '',
    code: rule?.code || '',
    description: rule?.description || '',
    condition_mode: rule?.condition_mode || 'and',
    priority: rule?.priority || 0,
    conditions: rule?.conditions || initialConditions || [{ field: 'severity', operator: 'in', value: ['critical'] }],
    selected_channels: (() => {
      const channels: number[] = []
      const actions = rule?.actions || []
      for (const action of actions) {
        if (typeof action === 'object' && action !== null) {
          channels.push(action.channel_id)
        } else if (typeof action === 'string' || typeof action === 'number') {
          channels.push(Number(action))
        }
      }
      return channels
    })(),
  })

  // 监听 initialConditions 变化
  useEffect(() => {
    if (initialConditions && initialConditions.length > 0 && !rule) {
      setFormData(prev => ({ ...prev, conditions: initialConditions }))
    }
  }, [initialConditions, rule])

  const { data: channels = [] } = useQuery<any[]>({
    queryKey: ['channels'],
    queryFn: () => apiClient.get('/channels', { is_active: true }),
  })

  const { data: templates = [] } = useQuery<NotificationTemplate[]>({
    queryKey: ['templates'],
    queryFn: () => apiClient.get('/templates'),
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/rules', data),
    onSuccess,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/rules/${rule?.id}`, data),
    onSuccess,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // New action format with channel->template mapping
    const actions = formData.selected_channels.map((channelId: number) => ({
      channel_id: channelId,
      template_id: channelTemplateMap[channelId] ?? undefined,
    }))
    const payload = {
      name: formData.name,
      code: rule ? formData.code : generateCode(formData.name),
      description: formData.description,
      conditions: formData.conditions,
      condition_mode: formData.condition_mode,
      priority: formData.priority,
      actions,
      deduplication_config: null,
      aggregate_config: null,
      suppress_config: null,
    }
    if (rule) {
      updateMutation.mutate(payload)
    } else {
      createMutation.mutate(payload)
    }
  }

  return (
    <Modal
      open={true}
      onOpenChange={(open) => { if (!open) onClose() }}
      title={rule ? '编辑路由规则' : initialConditions?.length ? '快捷创建路由规则' : '创建路由规则'}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label>规则名称</Label>
            <Input
              type="text"
              required
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div className="space-y-2">
            <Label>描述</Label>
            <Textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>条件组合方式</Label>
              <Select value={formData.condition_mode} onValueChange={(v) => setFormData({ ...formData, condition_mode: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="and">AND (全部满足)</SelectItem>
                  <SelectItem value="or">OR (任一满足)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>优先级</Label>
              <Input
                type="number"
                min="0"
                max="1000"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>条件</Label>
            <ConditionEditor
              conditions={formData.conditions}
              onChange={(conditions) => setFormData({ ...formData, conditions })}
              fields={FIELD_CONFIGS}
            />
          </div>

          <div className="space-y-2">
            <Label>通知渠道</Label>
            <div className="space-y-2">
              {channels.length === 0 ? (
                <div className="text-sm text-muted-foreground">暂无可用渠道，请先创建通知渠道</div>
              ) : (
                channels.map((channel: any) => {
                  const isSelected = formData.selected_channels.includes(channel.id)
                  const channelTemplates = (templates as NotificationTemplate[]).filter(
                    (t: NotificationTemplate) => t.channel_type === channel.channel_type
                  )
                  const selectedTemplateId = channelTemplateMap[channel.id] ?? null

                  return (
                    <div key={channel.id} className="p-2 border rounded-md hover:bg-muted/50 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormData({
                                ...formData,
                                selected_channels: [...formData.selected_channels, channel.id],
                              })
                            } else {
                              setFormData({
                                ...formData,
                                selected_channels: formData.selected_channels.filter((id: number) => id !== channel.id),
                              })
                              const newMap = { ...channelTemplateMap }
                              delete newMap[channel.id]
                              setChannelTemplateMap(newMap)
                            }
                          }}
                          className="rounded"
                        />
                        <span className="font-medium">{channel.name}</span>
                        <span className="text-sm text-muted-foreground">({channel.channel_type})</span>
                      </div>

                      {isSelected && channelTemplates.length > 0 && (
                        <div className="ml-6 flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">模板:</span>
                          <Select
                            value={selectedTemplateId?.toString() || ''}
                            onValueChange={(v) => {
                              setChannelTemplateMap({
                                ...channelTemplateMap,
                                [channel.id]: v ? Number(v) : null,
                              })
                            }}
                          >
                            <SelectTrigger className="w-[180px] h-8">
                              <SelectValue placeholder="使用渠道默认" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="">使用渠道默认</SelectItem>
                              {channelTemplates.map((t: NotificationTemplate) => (
                                <SelectItem key={t.id} value={t.id.toString()}>
                                  {t.name}{t.is_default ? ' (默认)' : ''}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {!selectedTemplateId && (
                            <span className="text-xs text-muted-foreground flex items-center gap-0.5" title="未选择模板时使用渠道的默认模板">
                              <HelpCircle className="w-3 h-3" />
                              将使用渠道默认模板
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              取消
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {rule ? '保存' : '创建'}
            </Button>
          </div>
        </form>
    </Modal>
  )
}
