import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/services/api'
import { AlertResponse } from '@/types/alert'

export function AlertDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: alert, isLoading, error } = useQuery<AlertResponse>({
    queryKey: ['alert', id],
    queryFn: () => apiClient.get(`/alerts/${id}`),
    enabled: !!id,
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

  const [aiAnalysis, setAiAnalysis] = useState<any>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')

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

      const result = await apiClient.get(endpoint)
      setAiAnalysis({ action, data: result })
    } catch (err: any) {
      setAiError(err.response?.data?.detail || 'AI请求失败')
    } finally {
      setAiLoading(false)
    }
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
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
            onClick={() => handleAIAction('analyze')}
            disabled={aiLoading}
            className="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 disabled:opacity-50"
          >
            🤖 AI分析
          </button>
        </div>
      </div>

      {aiLoading && (
        <div className="bg-white rounded-lg shadow p-6 text-center">
          <div className="text-purple-600">🤖 AI分析中...</div>
        </div>
      )}

      {aiError && (
        <div className="bg-red-50 rounded-lg shadow p-6">
          <div className="text-red-600">{aiError}</div>
        </div>
      )}

      {aiAnalysis && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium mb-4">
            {aiAnalysis.action === 'analyze' && '🤖 根因分析'}
            {aiAnalysis.action === 'polish' && '✨ 润色内容'}
            {aiAnalysis.action === 'suggest' && '💡 建议操作'}
            {aiAnalysis.action === 'impact' && '📊 影响预测'}
          </h2>
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

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium mb-4">基本信息</h2>
          <dl className="space-y-3">
            <div className="flex">
              <dt className="w-24 text-gray-500">告警标题</dt>
              <dd className="font-medium">{alert.title}</dd>
            </div>
            <div className="flex">
              <dt className="w-24 text-gray-500">告警来源</dt>
              <dd>{alert.source}</dd>
            </div>
            <div className="flex">
              <dt className="w-24 text-gray-500">Alert Key</dt>
              <dd className="font-mono text-sm">{alert.alert_key}</dd>
            </div>
            <div className="flex">
              <dt className="w-24 text-gray-500">指纹</dt>
              <dd className="font-mono text-sm">{alert.fingerprint}</dd>
            </div>
            <div className="flex">
              <dt className="w-24 text-gray-500">触发时间</dt>
              <dd>{alert.fired_at ? new Date(alert.fired_at).toLocaleString('zh-CN') : '-'}</dd>
            </div>
            {alert.resolved_at && (
              <div className="flex">
                <dt className="w-24 text-gray-500">解决时间</dt>
                <dd>{new Date(alert.resolved_at).toLocaleString('zh-CN')}</dd>
              </div>
            )}
            <div className="flex">
              <dt className="w-24 text-gray-500">触发次数</dt>
              <dd>{alert.fire_count} (重复: {alert.repeat_count})</dd>
            </div>
            <div className="flex">
              <dt className="w-24 text-gray-500">升级次数</dt>
              <dd>{alert.escalation_count}</dd>
            </div>
          </dl>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium mb-4">告警内容</h2>
          <div className="text-gray-700 whitespace-pre-wrap">{alert.content || '无'}</div>
          {alert.metric_name && (
            <div className="mt-4 p-3 bg-gray-50 rounded">
              <div className="text-sm text-gray-500">指标名称</div>
              <div className="font-mono">{alert.metric_name}</div>
              {alert.metric_value && (
                <>
                  <div className="text-sm text-gray-500 mt-2">指标值</div>
                  <div className="font-mono">{JSON.stringify(alert.metric_value)}</div>
                </>
              )}
            </div>
          )}
        </div>

        {alert.labels && Object.keys(alert.labels).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium mb-4">标签</h2>
            <div className="space-y-2">
              {Object.entries(alert.labels).map(([key, value]) => (
                <div key={key} className="flex">
                  <span className="w-32 text-gray-500">{key}</span>
                  <span className="font-mono text-sm">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {alert.annotations && Object.keys(alert.annotations).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium mb-4">注解</h2>
            <div className="space-y-2">
              {Object.entries(alert.annotations).map(([key, value]) => (
                <div key={key} className="flex">
                  <span className="w-32 text-gray-500">{key}</span>
                  <span className="text-sm">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {alert.matched_rules && alert.matched_rules.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium mb-4">匹配规则</h2>
            <div className="space-y-2">
              {alert.matched_rules.map((rule: any, index: number) => (
                <div key={index} className="p-3 bg-gray-50 rounded">
                  <div className="font-medium">{rule.name}</div>
                  <div className="text-sm text-gray-500">优先级: {rule.priority}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {alert.raw_data && Object.keys(alert.raw_data).length > 0 && (
          <div className="bg-white rounded-lg shadow p-6 col-span-2">
            <h2 className="text-lg font-medium mb-4">原始数据</h2>
            <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-auto text-xs">
              {JSON.stringify(alert.raw_data, null, 2)}
            </pre>
          </div>
        )}
      </div>
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
