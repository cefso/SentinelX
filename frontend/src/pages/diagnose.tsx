import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/services/api'

interface DiagnosisSummary {
  status?: string
  suppress_reason?: string
  deduction_reason?: string
}

interface FlowStep {
  step: number
  type: string
  title: string
  description: string
  status: string
  details?: Record<string, unknown>
  reason?: string
  time?: string
}

interface DiagnosisData {
  trace_id: string
  summary: DiagnosisSummary
  matched_rules?: string[]
  flow_steps: FlowStep[]
  timeline?: { time: string; event: string }[]
}

export function DiagnosePage() {
  const [searchParams] = useSearchParams()
  const initialTrace = searchParams.get('trace') || ''
  const [traceId, setTraceId] = useState(initialTrace)
  const [searchedTraceId, setSearchedTraceId] = useState(initialTrace)

  useEffect(() => {
    if (initialTrace) {
      setSearchedTraceId(initialTrace)
    }
  }, [initialTrace])

  const { data, isLoading, error } = useQuery<DiagnosisData>({
    queryKey: ['diagnose', searchedTraceId],
    queryFn: () => apiClient.get(`/alerts/diagnose/${searchedTraceId}`),
    enabled: !!searchedTraceId,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchedTraceId(traceId)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">告警诊断</h1>
        <p className="text-gray-600">输入Trace ID查看告警处理全流程</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          value={traceId}
          onChange={(e) => setTraceId(e.target.value)}
          placeholder="输入 Trace ID (如 a1b2c3d4e5f6)"
          className="flex-1 px-3 py-2 border rounded-md"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
        >
          诊断
        </button>
      </form>

      {isLoading && <div className="text-center py-8">加载中...</div>}

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-md">
          未找到对应的Trace记录
        </div>
      )}

      {data && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium mb-4">处理结果</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-500">状态</div>
                <div className="text-lg font-medium">
                  <TraceStatusBadge status={data.summary?.status} />
                </div>
              </div>
              {data.summary?.suppress_reason && (
                <div className="col-span-2">
                  <div className="text-sm text-gray-500">抑制原因</div>
                  <div className="text-red-600">{data.summary.suppress_reason}</div>
                </div>
              )}
              {data.summary?.deduction_reason && (
                <div className="col-span-2">
                  <div className="text-sm text-gray-500">去重原因</div>
                  <div className="text-yellow-600">{data.summary.deduction_reason}</div>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-medium mb-4">处理流程</h2>
            <div className="space-y-3">
              {data.flow_steps?.map((step: any, index: number) => (
                <div key={index} className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-medium">
                    {step.step}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium">{step.title}</div>
                    <div className="text-sm text-gray-500">{step.description}</div>
                    {step.reason && (
                      <div className="text-sm text-red-500 mt-1">{step.reason}</div>
                    )}
                    {step.details && (
                      <div className="mt-2 text-xs text-gray-500 space-y-1">
                        {step.details.rule_name && (
                          <div>规则: {step.details.rule_name}</div>
                        )}
                        {step.details.blocked_by_rule && (
                          <div>触发规则: {step.details.blocked_by_rule}</div>
                        )}
                        {step.details.triggered_by_rule && (
                          <div>触发规则: {step.details.triggered_by_rule}</div>
                        )}
                        {step.details.matched_rules && (
                          <div>匹配规则: {step.details.matched_rules.map((r: any) => r.name).join(', ')}</div>
                        )}
                        {step.details.group_key && (
                          <div>聚合组: {step.details.group_key}</div>
                        )}
                        {step.details.channel_ids && (
                          <div>通知渠道: {step.details.channel_ids.join(', ')}</div>
                        )}
                      </div>
                    )}
                  </div>
                  <StatusIndicator status={step.status} stepType={step.type} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function TraceStatusBadge({ status }: { status?: string }) {
  const config: Record<string, { className: string; label: string }> = {
    duplicate: { className: 'bg-yellow-100 text-yellow-800', label: '已去重' },
    dedup_skipped: { className: 'bg-yellow-100 text-yellow-800', label: '已去重' },
    queued: { className: 'bg-green-100 text-green-800', label: '已入队' },
    suppressed: { className: 'bg-gray-100 text-gray-800', label: '已抑制' },
    aggregated: { className: 'bg-violet-100 text-violet-800', label: '已聚合' },
    failed: { className: 'bg-red-100 text-red-800', label: '失败' },
    no_channels: { className: 'bg-gray-100 text-gray-800', label: '无通知渠道' },
  }
  if (!status) return <span className="text-gray-500">-</span>
  const item = config[status] || { className: 'bg-gray-100 text-gray-800', label: status }
  return (
    <span className={`inline-flex px-2 py-1 text-sm rounded ${item.className}`}>
      {item.label}
    </span>
  )
}

function StatusIndicator({ status, stepType }: { status: string; stepType?: string }) {
  if (stepType === 'dedup_result' && status === 'blocked') {
    return (
      <span className="px-2 py-1 text-xs rounded bg-yellow-100 text-yellow-600">
        已去重
      </span>
    )
  }

  const config: Record<string, { bg: string; text: string; label: string }> = {
    success: { bg: 'bg-green-100', text: 'text-green-600', label: '成功' },
    passed: { bg: 'bg-blue-100', text: 'text-blue-600', label: '通过' },
    skipped: { bg: 'bg-gray-100', text: 'text-gray-600', label: '跳过' },
    blocked: { bg: 'bg-red-100', text: 'text-red-600', label: '阻止' },
    failed: { bg: 'bg-red-100', text: 'text-red-600', label: '失败' },
    processing: { bg: 'bg-yellow-100', text: 'text-yellow-600', label: '处理中' },
    aggregated: { bg: 'bg-purple-100', text: 'text-purple-600', label: '已聚合' },
    new_group: { bg: 'bg-indigo-100', text: 'text-indigo-600', label: '新组' },
    fallback: { bg: 'bg-gray-100', text: 'text-gray-600', label: '回退' },
    dedup_skipped: { bg: 'bg-yellow-100', text: 'text-yellow-600', label: '已去重' },
  }

  const statusConfig = config[status] || config.skipped

  return (
    <span className={`px-2 py-1 text-xs rounded ${statusConfig.bg} ${statusConfig.text}`}>
      {statusConfig.label}
    </span>
  )
}
