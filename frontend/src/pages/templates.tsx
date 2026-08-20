import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth-store'
import { FileText, Plus, Edit2, Trash2, Eye } from 'lucide-react'
import { CHANNEL_TYPES, CHANNEL_TYPE_LABELS, VARIABLE_DOCS, EXAMPLE_ALERT, renderJinja2Preview } from './templates/constants'
import { Modal } from '@/components/common/Modal'
import { FilterTabs } from '@/components/common/FilterTabs'
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

export interface NotificationTemplate {
  id: number
  name: string
  code: string
  channel_type: string
  content: string
  is_default: boolean
  is_active: boolean
  variables: any[]
  created_at: string
  updated_at: string
}

export function TemplatesPage() {
  const queryClient = useQueryClient()
  const { currentTenant, user } = useAuthStore()
  const [showModal, setShowModal] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplate | null>(null)
  const [filter, setFilter] = useState<string>('all')

  // 权限检查
  const permissions = currentTenant?.permissions || []
  const canWrite = permissions.includes('*') || permissions.includes('templates:write') || user?.is_system === true

  const { data: templates = [], isLoading } = useQuery<NotificationTemplate[]>({
    queryKey: ['templates'],
    queryFn: () => apiClient.get('/templates'),
  })

  const deleteMutation = useMutation({
    mutationFn: (templateId: number) => apiClient.delete(`/templates/${templateId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['templates'] }),
  })

  const filteredTemplates = filter === 'all'
    ? templates
    : templates.filter(t => t.channel_type === filter)

  const handleEdit = (template: NotificationTemplate) => {
    setEditingTemplate(template)
    setShowModal(true)
  }

  const handleCreate = () => {
    setEditingTemplate(null)
    setShowModal(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">通知模板</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            管理各渠道的通知模板，支持 Jinja2 变量
          </p>
        </div>
        {canWrite && (
          <Button onClick={handleCreate} className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            创建模板
          </Button>
        )}
      </div>

      {/* Channel type filter */}
      <FilterTabs
        tabs={[
          { key: 'all', label: '全部', count: templates.length },
          ...CHANNEL_TYPES.map((type) => ({
            key: type.value,
            label: type.label,
            count: templates.filter(t => t.channel_type === type.value).length,
          })),
        ]}
        active={filter}
        onChange={setFilter}
      />

      {/* Templates table */}
      <div className="bg-card rounded-lg border shadow-sm">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">加载中...</div>
        ) : filteredTemplates.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 mx-auto text-muted-foreground/50 mb-3" />
            <div className="text-muted-foreground font-medium">暂无通知模板</div>
            <div className="text-sm text-muted-foreground/70 mt-1">创建模板为不同渠道定制通知内容</div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">模板名称</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">渠道类型</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">内容预览</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground w-24">默认模板</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-muted-foreground w-32">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {filteredTemplates.map((template) => (
                  <tr key={template.id} className="hover:bg-muted/50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-foreground">{template.name}</div>
                      <div className="text-xs text-muted-foreground">
                        更新于 {new Date(template.updated_at).toLocaleDateString('zh-CN')}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 text-xs rounded bg-primary/10 text-primary font-medium">
                        {CHANNEL_TYPE_LABELS[template.channel_type] || template.channel_type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm text-muted-foreground max-w-md truncate font-mono">
                        {template.content || '-'}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {template.is_default ? (
                        <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800 font-medium">默认</span>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      {canWrite && (
                        <>
                          <button
                            onClick={() => handleEdit(template)}
                            className="text-primary hover:text-primary/80 mr-3 inline-flex items-center gap-1"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                            编辑
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('确定要删除该模板吗？')) {
                                deleteMutation.mutate(template.id)
                              }
                            }}
                            disabled={deleteMutation.isPending}
                            className="text-destructive hover:text-destructive/80 disabled:opacity-50 inline-flex items-center gap-1"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
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
        <TemplateModal
          template={editingTemplate}
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false)
            queryClient.invalidateQueries({ queryKey: ['templates'] })
          }}
        />
      )}
    </div>
  )
}

function TemplateModal({
  template,
  onClose,
  onSuccess,
}: {
  template: NotificationTemplate | null
  onClose: () => void
  onSuccess: () => void
}) {
  const [formData, setFormData] = useState({
    name: template?.name || '',
    channel_type: template?.channel_type || 'dingtalk',
    is_default: template?.is_default ?? false,
    content: template?.content || '',
  })
  const [showPreview, setShowPreview] = useState(false)
  const [previewContent, setPreviewContent] = useState('')

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/templates', data),
    onSuccess,
  })

  const updateMutation = useMutation({
    mutationFn: (data: any) => apiClient.put(`/templates/${template?.id}`, data),
    onSuccess,
  })

  const handlePreview = () => {
    const rendered = renderJinja2Preview(formData.content, EXAMPLE_ALERT)
    setPreviewContent(rendered)
    setShowPreview(true)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (template) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const channelType = formData.channel_type
  const varDocs = VARIABLE_DOCS[channelType] || VARIABLE_DOCS.dingtalk

  return (
    <>
      <Modal
        open={true}
        onOpenChange={(open) => { if (!open) onClose() }}
        title={template ? '编辑模板' : '创建模板'}
        size="xl"
        footer={
          <>
            <Button type="button" variant="outline" onClick={onClose}>
              取消
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              form="template-form"
            >
              {template ? '保存' : '创建'}
            </Button>
          </>
        }
      >
        <form id="template-form" onSubmit={handleSubmit} className="space-y-4">
            {/* Name and channel type */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>模板名称</Label>
                <Input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="如: 严重告警通知"
                />
              </div>
              <div className="space-y-2">
                <Label>渠道类型</Label>
                <Select value={formData.channel_type} onValueChange={(v) => setFormData({ ...formData, channel_type: v })} disabled={!!template}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHANNEL_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Is default */}
            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="rounded"
                />
                <span className="text-sm">设为默认模板</span>
                <span className="text-xs text-muted-foreground">（该渠道未指定模板时使用）</span>
              </label>
            </div>

            {/* Content editor */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <Label>模板内容 (Jinja2)</Label>
                <button
                  type="button"
                  onClick={handlePreview}
                  className="text-sm text-primary hover:text-primary/80 flex items-center gap-1"
                >
                  <Eye className="w-3.5 h-3.5" />
                  预览
                </button>
              </div>
              <Textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                className="font-mono text-sm"
                rows={12}
                placeholder={`如: 【{{ alert.severity | upper }}】{{ alert.title }}\n\n告警内容: {{ alert.content }}\n来源: {{ alert.source }}\n时间: {{ alert.fired_at }}`}
              />
            </div>

            {/* Variables docs */}
            <div className="bg-muted rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium text-foreground">{varDocs.label}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-8 gap-y-1">
                {varDocs.variables.map((v, i) => (
                  <div key={i} className="text-xs text-muted-foreground font-mono">{v}</div>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t border-border">
                <div className="text-xs font-medium text-muted-foreground mb-1">Jinja2 条件示例</div>
                <div className="text-xs text-muted-foreground font-mono">
                  {`{% if alert.severity == 'critical' %}`}<br />
                  {'  【紧急】{{ alert.title }}'}<br />
                  {`{% endif %}`}
                </div>
              </div>
            </div>
          </form>
      </Modal>

      {/* Preview modal */}
      {showPreview && (
        <Modal
          open={showPreview}
          onOpenChange={setShowPreview}
          title="模板预览"
          size="lg"
        >
          <div className="space-y-4">
            <div className="text-xs text-muted-foreground mb-2">示例告警数据:</div>
            <div className="bg-muted rounded p-2 text-xs font-mono text-muted-foreground mb-4 overflow-x-auto whitespace-pre">
{JSON.stringify(EXAMPLE_ALERT, null, 2)}
            </div>
            <div className="text-xs text-muted-foreground mb-2">渲染结果:</div>
            <pre className="bg-primary/5 rounded p-4 text-sm whitespace-pre-wrap break-all border border-primary/20">
              {previewContent || '(空)'}
            </pre>
          </div>
        </Modal>
      )}
    </>
  )
}
