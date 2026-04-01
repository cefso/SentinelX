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
                <div className="text-lg font-medium">{data.summary?.status}</div>
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
                  </div>
                  <StatusIndicator status={step.status} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StatusIndicator({ status }: { status: string }) {
  const config = {
    success: 'bg-green-100 text-green-600',
    passed: 'bg-blue-100 text-blue-600',
    skipped: 'bg-gray-100 text-gray-600',
    blocked: 'bg-red-100 text-red-600',
    failed: 'bg-red-100 text-red-600',
  }

  return (
    <span className={`px-2 py-1 text-xs rounded ${config[status as keyof typeof config] || config.skipped}`}>
      {status}
    </span>
  )
}
