import { useState } from 'react'
import { RuleModal } from '../rules'
import type { Condition } from '../rules'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { AlertResponse } from '@/types/alert'
import { useCloudMetricsMap, useProductName, useMetricDesc } from '@/hooks/useCloudMetrics'
import { Send, CheckCircle, AlertCircle, XCircle, Clock, Circle, ChevronDown } from 'lucide-react'

export function AlertDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [showAllLabels, setShowAllLabels] = useState(false)
  const [showAllAnnotations, setShowAllAnnotations] = useState(false)
  const [showRuleModal, setShowRuleModal] = useState(false)
  const [ruleInitialConditions, setRuleInitialConditions] = useState<Condition[]>([])

  function generateInitialConditions(alertData: AlertResponse): Condition[] {
    const conditions: Condition[] = []

    // 预填充 labels，key 为第一个 label 的 key
    if (alertData.labels && Object.keys(alertData.labels).length > 0) {
      const firstKey = Object.keys(alertData.labels)[0]
      conditions.push({
        field: 'labels',
        operator: 'eq',
        value: alertData.labels[firstKey],
        key: firstKey,  // 传递 key 给 RuleModal 用于初始化 labelsKey
      })
    }

    // 补充其他关键字段
    if (conditions.length < 5 && alertData.namespace) {
      conditions.push({ field: 'namespace', operator: 'eq', value: alertData.namespace })
    }

    if (conditions.length < 5 && alertData.metric_name) {
      conditions.push({ field: 'metric_name', operator: 'eq', value: alertData.metric_name })
    }

    if (conditions.length < 5 && alertData.source) {
      conditions.push({ field: 'source', operator: 'eq', value: alertData.source })
    }

    if (conditions.length < 5 && alertData.severity) {
      conditions.push({ field: 'severity', operator: 'eq', value: alertData.severity })
    }

    return conditions.slice(0, 5)
  }

  const handleCreateRule = () => {
    if (alert) {
      const conditions = generateInitialConditions(alert)
      setRuleInitialConditions(conditions)
      setShowRuleModal(true)
    }
  }

  const { data: alert, isLoading, error } = useQuery<AlertResponse>({
    queryKey: ['alert', id],
    queryFn: () => apiClient.get(`/alerts/${id}`),
    enabled: !!id,
  })

  const { data: fpAlerts } = useQuery<{ items: AlertResponse[]; total: number }>({
    queryKey: ['alertsByFp', alert?.fingerprint],
    queryFn: () => apiClient.get('/alerts', {
      page: 1,
      page_size: 100,
      fingerprint: alert!.fingerprint,
    }),
    enabled: !!alert?.fingerprint,
  })

  const { data: cloudMetricsMap } = useCloudMetricsMap()

  const productName = useProductName(alert?.namespace || '', cloudMetricsMap)
  const metricDesc = useMetricDesc(alert?.namespace || '', alert?.metric_name || '', cloudMetricsMap)

  const { data: users = [] } = useQuery<{ id: number; username: string }[]>({
    queryKey: ['users-for-assign'],
    queryFn: () => apiClient.get('/users'),
  })

  const updateMutation = useMutation({
    mutationFn: (data: Partial<AlertResponse>) =>
      apiClient.put(`/alerts/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alert', id] })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alertStats'] })
    },
  })

  const handleAcknowledge = () => {
    if (alert) {
      updateMutation.mutate({ status: 'acknowledged' })
    }
  }

  const handleResolve = () => {
    if (alert) {
      updateMutation.mutate({ status: 'resolved' })
    }
  }

  const handleAssign = (assigneeId: number | null) => {
    if (alert) {
      updateMutation.mutate({ assignee_id: assigneeId ?? undefined })
    }
  }

  const [aiAnalysis, setAiAnalysis] = useState<any>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')
  const [aggregatedExpanded, setAggregatedExpanded] = useState(false)

  const { data: aggregatedAlerts = [], isLoading: aggregatedLoading } = useQuery<AlertResponse[]>({
    queryKey: ['alertAggregated', alert?.id],
    queryFn: () => apiClient.get(`/alerts/${alert!.id}/aggregated-members`),
    enabled: !!alert?.id,
  })

  const handleAIAction = async (action: string) => {
    if (!alert) return
    setAiLoading(true)
    setAiError('')
    setAiAnalysis(null)

    try {
      const endpoint = {
        'analyze': `/alerts/${alert.id}/analyze`,
        'polish': `/alerts/${alert.id}/polish`,
        'suggest': `/alerts/${alert.id}/suggest-actions`,
        'impact': `/alerts/${alert.id}/predict-impact`,
      }[action] as string

      const result = await apiClient.post(endpoint, {})
      setAiAnalysis({ action, data: result })
    } catch (err: any) {
      setAiError(err.response?.data?.detail || 'AI请求失败')
    } finally {
      setAiLoading(false)
    }
  }

  // 构建时间线
  const timeline = []
  if (alert?.fired_at) {
    timeline.push({ time: alert.fired_at, event: '告警触发', icon: AlertCircle, color: 'text-red-500' })
  }
  if (alert?.acknowledged_at) {
    timeline.push({ time: alert.acknowledged_at, event: '已确认', icon: CheckCircle, color: 'text-yellow-500' })
  }
  if (alert?.resolved_at) {
    timeline.push({ time: alert.resolved_at, event: '已解决', icon: CheckCircle, color: 'text-green-500' })
  }
  if (alert?.silenced_until) {
    timeline.push({ time: alert.silenced_until, event: '已静默', icon: XCircle, color: 'text-gray-500' })
  }

  if (isLoading) {
    return <div className="p-8 text-center">加载中...</div>
  }

  if (error || !alert) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-600">未找到该告警</div>
        <button onClick={() => navigate('/alerts')} className="mt-4 text-blue-600 hover:underline">
          返回列表
        </button>
      </div>
    )
  }

  const labelEntries = Object.entries(alert.labels || {})
  const annotationEntries = Object.entries(alert.annotations || {})
  const displayedLabels = showAllLabels ? labelEntries : labelEntries.slice(0, 5)
  const displayedAnnotations = showAllAnnotations ? annotationEntries : annotationEntries.slice(0, 5)

  return (
    <div className="space-y-6">
      {/* 顶部操作栏 */}
      <div className="flex items-center justify-between bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/alerts')} className="text-gray-500 hover:text-gray-700">
            ← 返回
          </button>
          <h1 className="text-2xl font-bold">告警详情</h1>
          <SeverityBadge severity={alert.severity} />
          <StatusBadge status={alert.status} />
        </div>
        <div className="flex gap-2">
          {alert.status === 'firing' && (
            <button
              onClick={handleAcknowledge}
              disabled={updateMutation.isPending}
              className="px-4 py-2 bg-yellow-500 text-white rounded-md hover:bg-yellow-600 disabled:opacity-50"
            >
              确认
            </button>
          )}
          {(alert.status === 'firing' || alert.status === 'acknowledged') && (
            <button
              onClick={handleResolve}
              disabled={updateMutation.isPending}
              className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 disabled:opacity-50"
            >
              解决
            </button>
          )}
          {alert.trace_id && (
            <button
              onClick={() => navigate(`/diagnose?trace=${alert.trace_id}`)}
              className="px-4 py-2 border rounded-md hover:bg-gray-50"
            >
              诊断
            </button>
          )}
          <button
            onClick={handleCreateRule}
            className="px-4 py-2 border rounded-md hover:bg-gray-50"
          >
            创建规则
          </button>
          <div className="relative group">
            <button
              className="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600"
            >
              🤖 AI
            </button>
            <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg shadow-lg border hidden group-hover:block z-10">
              <button onClick={() => handleAIAction('analyze')} disabled={aiLoading} className="w-full px-4 py-2 text-left hover:bg-gray-50 text-sm rounded-t-lg disabled:opacity-50">🔍 根因分析</button>
              <button onClick={() => handleAIAction('polish')} disabled={aiLoading} className="w-full px-4 py-2 text-left hover:bg-gray-50 text-sm disabled:opacity-50">✨ 内容润色</button>
              <button onClick={() => handleAIAction('suggest')} disabled={aiLoading} className="w-full px-4 py-2 text-left hover:bg-gray-50 text-sm disabled:opacity-50">💡 建议操作</button>
              <button onClick={() => handleAIAction('impact')} disabled={aiLoading} className="w-full px-4 py-2 text-left hover:bg-gray-50 text-sm rounded-b-lg disabled:opacity-50">📊 影响预测</button>
            </div>
          </div>
        </div>
      </div>

      {/* AI分析结果 */}
      {aiLoading && (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="text-purple-600 animate-pulse">🤖 AI分析中...</div>
        </div>
      )}

      {aiError && (
        <div className="bg-red-50 rounded-lg shadow p-6">
          <div className="text-red-600">{aiError}</div>
        </div>
      )}

      {aiAnalysis && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium">
              {aiAnalysis.action === 'analyze' && '🤖 根因分析'}
              {aiAnalysis.action === 'polish' && '✨ 润色内容'}
              {aiAnalysis.action === 'suggest' && '💡 建议操作'}
              {aiAnalysis.action === 'impact' && '📊 影响预测'}
            </h2>
            <button onClick={() => setAiAnalysis(null)} className="text-gray-500 hover:text-gray-700">×</button>
          </div>
          <div className="prose prose-sm max-w-none">
            {aiAnalysis.action === 'suggest' ? (
              <ul className="list-disc pl-5 space-y-1">
                {(aiAnalysis.data.suggested_actions || []).map((action: string, i: number) => (
                  <li key={i}>{action}</li>
                ))}
              </ul>
            ) : (
              <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-4 rounded overflow-auto">
                {aiAnalysis.data.analysis || aiAnalysis.data.polished_content || aiAnalysis.data.predicted_impact}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* 主要内容区域 */}
      <div className="grid grid-cols-3 gap-6">
        {/* 左列 - col-span-2，所有卡片 */}
        <div className="col-span-2 space-y-4">
          {/* 基本信息卡片 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">基本信息</h2>
            <dl className="grid grid-cols-3 gap-x-6 gap-y-2 text-sm">
              <div className="flex flex-col">
                <dt className="text-gray-500">告警标题</dt>
                <dd className="font-medium break-words">{alert.title}</dd>
              </div>
              <div className="flex flex-col">
                <dt className="text-gray-500">告警来源</dt>
                <dd className="font-medium">{alert.source}</dd>
              </div>
              <div className="flex flex-col">
                <dt className="text-gray-500">Alert Key</dt>
                <dd className="font-mono text-xs">{alert.alert_key}</dd>
              </div>
              <div className="flex flex-col">
                <dt className="text-gray-500">产品</dt>
                <dd className="font-medium truncate">{productName || alert?.namespace || '-'}</dd>
              </div>
              <div className="flex flex-col">
                <dt className="text-gray-500">实例</dt>
                <dd className="font-medium truncate">{alert?.instance_name || alert?.instance_id || '-'}</dd>
              </div>
              <div className="flex flex-col">
                <dt className="text-gray-500">触发次数</dt>
                <dd>{alert.fire_count} (重复: {alert.repeat_count})</dd>
              </div>
              <div className="flex flex-col">
                <dt className="text-gray-500">升级次数</dt>
                <dd>{alert.escalation_count}</dd>
              </div>
              <div className="flex flex-col">
                <dt className="text-gray-500">指纹</dt>
                <dd className="font-mono text-xs break-all">{alert.fingerprint}</dd>
              </div>
              {alert.trace_id && (
                <div className="flex flex-col">
                  <dt className="text-gray-500">Trace ID</dt>
                  <dd className="font-mono text-xs text-blue-600">{alert.trace_id}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* 告警内容卡片 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">告警内容</h2>
            <div className="text-gray-700 whitespace-pre-wrap text-sm">{alert.content || '无'}</div>
            {alert.metric_name && (
              <div className="mt-3 p-3 bg-gray-50 rounded text-sm">
                <div className="text-gray-500">指标名称</div>
                <div className="font-mono">{metricDesc || alert.metric_name}</div>
                {alert.metric_value && (
                  <>
                    <div className="text-gray-500 mt-1">指标值</div>
                    <div className="font-mono">{JSON.stringify(alert.metric_value)}</div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* 标签卡片 */}
          {labelEntries.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">标签</h2>
                {labelEntries.length > 5 && (
                  <button
                    onClick={() => setShowAllLabels(!showAllLabels)}
                    className="text-xs text-blue-600 hover:text-blue-700"
                  >
                    {showAllLabels ? '收起' : `查看全部 (${labelEntries.length})`}
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {displayedLabels.map(([key, value]) => (
                  <span key={key} className="inline-flex items-center px-2 py-1 bg-gray-100 rounded text-sm">
                    <span className="text-gray-500">{key}:</span>
                    <span className="font-mono ml-1">{String(value)}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 注解卡片 */}
          {annotationEntries.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">注解</h2>
                {annotationEntries.length > 5 && (
                  <button
                    onClick={() => setShowAllAnnotations(!showAllAnnotations)}
                    className="text-xs text-blue-600 hover:text-blue-700"
                  >
                    {showAllAnnotations ? '收起' : `查看全部 (${annotationEntries.length})`}
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                {displayedAnnotations.map(([key, value]) => (
                  <div key={key} className="flex flex-col text-sm">
                    <span className="text-gray-500">{key}</span>
                    <span>{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 处理时间线卡片 */}
          {timeline.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">处理时间线</h2>
              <div className="relative">
                <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-gray-200" />
                <div className="space-y-2">
                  {timeline.map((item, index) => {
                    const Icon = item.icon
                    return (
                      <div key={index} className="relative flex items-start gap-3 pl-8">
                        <div className={`absolute left-0 w-4 h-4 rounded-full bg-white border-2 ${item.color.replace('text-', 'border-')}`}>
                          <Icon className={`w-3 h-3 absolute top-0.5 left-0.5 ${item.color}`} />
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-sm">{item.event}</div>
                          <div className="text-xs text-gray-500">
                            {new Date(item.time).toLocaleString('zh-CN')}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {/* 匹配规则卡片 */}
          {alert.matched_rules && alert.matched_rules.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">匹配规则</h2>
              <div className="grid grid-cols-2 gap-2">
                {alert.matched_rules.map((rule: any, index: number) => (
                  <div key={index} className="p-2 bg-gray-50 rounded text-sm">
                    <div className="font-medium">{rule.name}</div>
                    <div className="text-gray-500 text-xs">优先级: {rule.priority}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 通知渠道卡片 */}
          {alert.notification_channels && alert.notification_channels.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">通知渠道</h2>
              <div className="flex flex-wrap gap-2">
                {alert.notification_channels.map((channel: any, index: number) => (
                  <span key={index} className="inline-flex items-center px-2 py-1 bg-blue-50 text-blue-700 rounded text-sm">
                    <Send className="w-3 h-3 mr-1" />
                    {channel.name || channel}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* 右列 - 三个卡片：处理人 / 原始数据 / 同指纹告警 */}
        <div className="space-y-4">
          {/* 处理人卡片 */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">处理人</h2>
            <select
              value={alert.assignee_id || ''}
              onChange={(e) => handleAssign(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="">未指派</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>{user.username}</option>
              ))}
            </select>
          </div>

          {/* 原始数据卡片 */}
          {alert.raw_data && Object.keys(alert.raw_data).length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">原始数据</h2>
              <pre className="bg-gray-900 text-gray-100 p-3 rounded overflow-auto text-xs max-h-40">
                {JSON.stringify(alert.raw_data, null, 2)}
              </pre>
            </div>
          )}

          {/* 同指纹告警卡片 */}
          {fpAlerts && fpAlerts.items.length > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-2 mb-3">
                <Clock className="w-4 h-4 text-gray-500" />
                <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">同指纹告警 ({fpAlerts.total})</h2>
              </div>
              <div className="relative">
                <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-gray-200" />
                <div className="space-y-2">
                  {fpAlerts.items
                    .sort((a, b) => new Date(b.fired_at).getTime() - new Date(a.fired_at).getTime())
                    .map((item) => (
                      <div
                        key={item.id}
                        className={`relative flex items-start gap-2 pl-8 py-1.5 cursor-pointer hover:bg-gray-50 rounded ${
                          item.id === alert.id ? 'bg-blue-50' : ''
                        }`}
                        onClick={() => item.id !== alert.id && navigate(`/alerts/${item.id}`)}
                      >
                        <div className="absolute left-0 top-1.5 w-5 h-5 rounded-full flex items-center justify-center">
                          {item.status === 'firing' ? (
                            <Circle className="w-2.5 h-2.5 text-red-500 fill-red-100" />
                          ) : item.status === 'resolved' ? (
                            <Circle className="w-2.5 h-2.5 text-green-500 fill-green-100" />
                          ) : item.status === 'acknowledged' ? (
                            <Circle className="w-2.5 h-2.5 text-yellow-500 fill-yellow-100" />
                          ) : (
                            <Circle className="w-2.5 h-2.5 text-gray-400 fill-gray-100" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5">
                            <SeverityBadge severity={item.severity} />
                            <span className="text-xs text-gray-400 truncate">
                              {new Date(item.fired_at).toLocaleString('zh-CN')}
                            </span>
                            {item.id === alert.id && (
                              <span className="text-xs text-blue-600 font-medium shrink-0">当前</span>
                            )}
                          </div>
                          <div className="text-xs text-gray-600 truncate">{item.title}</div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
      {/* 聚合告警折叠区域 */}
      {!aggregatedLoading && aggregatedAlerts.length > 1 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <button
            onClick={() => setAggregatedExpanded(!aggregatedExpanded)}
            className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-700">聚合告警</span>
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">
                {aggregatedAlerts.length}条
              </span>
            </div>
            <ChevronDown
              className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${
                aggregatedExpanded ? 'rotate-180' : ''
              }`}
            />
          </button>
          {aggregatedExpanded && (
            <div className="border-t">
              <div className="divide-y">
                {aggregatedAlerts.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-center gap-3 px-6 py-3 ${
                      item.id === alert.id ? 'bg-yellow-50' : 'hover:bg-gray-50'
                    } cursor-pointer transition-colors`}
                    onClick={() => item.id !== alert.id && navigate(`/alerts/${item.id}`)}
                  >
                    <span className={`w-2 h-2 rounded-full shrink-0 ${
                      item.severity === 'critical' ? 'bg-red-500' :
                      item.severity === 'high' ? 'bg-orange-500' :
                      item.severity === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                    }`} />
                    <span className="text-xs text-gray-500 shrink-0">
                      {new Date(item.fired_at).toLocaleString('zh-CN')}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${
                      item.severity === 'critical' ? 'bg-red-100 text-red-800' :
                      item.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                      item.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
                    }`}>{item.severity?.toUpperCase()}</span>
                    <span className="flex-1 text-sm text-gray-800 truncate">{item.title}</span>
                    {item.id === alert.id && (
                      <span className="text-xs text-yellow-600 shrink-0 font-medium">当前告警</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {showRuleModal && (
        <RuleModal
          rule={null}
          initialConditions={ruleInitialConditions}
          showModal={showRuleModal}
          onClose={() => setShowRuleModal(false)}
          onSuccess={() => {
            setShowRuleModal(false)
            queryClient.invalidateQueries({ queryKey: ['rules'] })
          }}
        />
      )}
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-100 text-red-800',
    high: 'bg-orange-100 text-orange-800',
    medium: 'bg-yellow-100 text-yellow-800',
    low: 'bg-blue-100 text-blue-800',
    info: 'bg-gray-100 text-gray-800',
  }

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${colors[severity] || colors.info}`}>
      {severity.toUpperCase()}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    firing: 'bg-red-100 text-red-800',
    resolved: 'bg-green-100 text-green-800',
    suppressed: 'bg-gray-100 text-gray-800',
    acknowledged: 'bg-yellow-100 text-yellow-800',
  }

  const labels: Record<string, string> = {
    firing: '触发中',
    resolved: '已恢复',
    suppressed: '已抑制',
    acknowledged: '已确认',
  }

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${colors[status] || colors.firing}`}>
      {labels[status] || status}
    </span>
  )
}
