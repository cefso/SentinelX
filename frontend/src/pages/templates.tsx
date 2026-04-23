import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { FileText, Plus, Edit2, Trash2, Eye } from 'lucide-react'
import { CHANNEL_TYPES, CHANNEL_TYPE_LABELS, VARIABLE_DOCS, EXAMPLE_ALERT, renderJinja2Preview } from './templates/constants'
import { Modal } from '@/components/common/Modal'

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
  const [showModal, setShowModal] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplate | null>(null)
  const [filter, setFilter] = useState<string>('all')

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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">通知模板</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            管理各渠道的通知模板，支持 Jinja2 变量
          </p>
        </div>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          创建模板
        </button>
      </div>

      {/* Channel type filter */}
      <div className="flex gap-2 flex-wrap items-center">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1.5 rounded text-sm transition-colors ${
            filter === 'all'
              ? 'bg-blue-100 text-blue-700 font-medium'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
        >
          全部 ({templates.length})
        </button>
        {CHANNEL_TYPES.map((type) => {
          const count = templates.filter(t => t.channel_type === type.value).length
          return (
            <button
              key={type.value}
              onClick={() => setFilter(type.value)}
              className={`px-3 py-1.5 rounded text-sm transition-colors ${
                filter === type.value
                  ? 'bg-blue-100 text-blue-700 font-medium'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {type.label} ({count})
            </button>
          )
        })}
      </div>

      {/* Templates table */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">加载中...</div>
        ) : filteredTemplates.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 mx-auto text-gray-300 mb-3" />
            <div className="text-gray-500 font-medium">暂无通知模板</div>
            <div className="text-sm text-gray-400 mt-1">创建模板为不同渠道定制通知内容</div>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">模板名称</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">渠道类型</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">内容预览</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">默认模板</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-32">操作</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredTemplates.map((template) => (
                <tr key={template.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{template.name}</div>
                    <div className="text-xs text-gray-400">
                      更新于 {new Date(template.updated_at).toLocaleDateString('zh-CN')}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 text-xs rounded bg-blue-50 text-blue-700 font-medium">
                      {CHANNEL_TYPE_LABELS[template.channel_type] || template.channel_type}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-sm text-gray-500 max-w-md truncate font-mono">
                      {template.content || '-'}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {template.is_default ? (
                      <span className="px-2 py-1 text-xs rounded bg-green-100 text-green-800 font-medium">默认</span>
                    ) : (
                      <span className="text-xs text-gray-400">-</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      onClick={() => handleEdit(template)}
                      className="text-blue-600 hover:text-blue-800 mr-3 inline-flex items-center gap-1"
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
                      className="text-red-600 hover:text-red-800 disabled:opacity-50 inline-flex items-center gap-1"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-md hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              form="template-form"
            >
              {template ? '保存' : '创建'}
            </button>
          </>
        }
      >
        <form id="template-form" onSubmit={handleSubmit} className="space-y-4">
            {/* Name and channel type */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">模板名称</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  placeholder="如: 严重告警通知"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">渠道类型</label>
                <select
                  value={formData.channel_type}
                  onChange={(e) => setFormData({ ...formData, channel_type: e.target.value })}
                  className="w-full px-3 py-2 border rounded-md"
                  disabled={!!template}
                >
                  {CHANNEL_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>{type.label}</option>
                  ))}
                </select>
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
                <span className="text-xs text-gray-400">（该渠道未指定模板时使用）</span>
              </label>
            </div>

            {/* Content editor */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm font-medium text-gray-700">模板内容 (Jinja2)</label>
                <button
                  type="button"
                  onClick={handlePreview}
                  className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
                >
                  <Eye className="w-3.5 h-3.5" />
                  预览
                </button>
              </div>
              <textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                className="w-full px-3 py-2 border rounded-md font-mono text-sm"
                rows={12}
                placeholder={`如: 【{{ alert.severity | upper }}】{{ alert.title }}\n\n告警内容: {{ alert.content }}\n来源: {{ alert.source }}\n时间: {{ alert.fired_at }}`}
              />
            </div>

            {/* Variables docs */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-medium text-gray-700">{varDocs.label}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-8 gap-y-1">
                {varDocs.variables.map((v, i) => (
                  <div key={i} className="text-xs text-gray-600 font-mono">{v}</div>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="text-xs font-medium text-gray-500 mb-1">Jinja2 条件示例</div>
                <div className="text-xs text-gray-500 font-mono">
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
            <div className="text-xs text-gray-400 mb-2">示例告警数据:</div>
            <div className="bg-gray-50 rounded p-2 text-xs font-mono text-gray-600 mb-4 overflow-x-auto whitespace-pre">
{JSON.stringify(EXAMPLE_ALERT, null, 2)}
            </div>
            <div className="text-xs text-gray-400 mb-2">渲染结果:</div>
            <pre className="bg-blue-50 rounded p-4 text-sm whitespace-pre-wrap break-all border border-blue-100">
              {previewContent || '(空)'}
            </pre>
          </div>
        </Modal>
      )}
    </>
  )
}
