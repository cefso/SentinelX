import { useState } from 'react'
import { apiClient } from '@/services/api'
import type { AlertResponse } from '@/types/alert'

export function AIActions({ alert }: { alert: AlertResponse }) {
  const [aiAnalysis, setAiAnalysis] = useState<any>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')
  const [, setShowMenu] = useState(false)

  const handleAIAction = async (action: string) => {
    setAiLoading(true)
    setAiError('')
    setAiAnalysis(null)
    setShowMenu(false)

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

  return (
    <>
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
    </>
  )
}
