import { useState } from 'react'
import axios from 'axios'
import { apiClient } from '@/services/api'
import type { AlertResponse } from '@/types/alert'
import { AIContentRenderer } from '@/components/ai/AIContentRenderer'

const STATUS_LABEL: Record<string, string> = {
  pending: '任务已提交，排队中…',
  running: '正在调用 AI 模型…',
}

const ACTION_TITLE: Record<string, string> = {
  analyze: '🤖 根因分析',
  polish: '✨ 润色内容',
  suggest: '💡 建议操作',
  impact: '📊 影响预测',
}

export type AlertAIState = {
  aiLoading: boolean
  aiLoadingHint: string
  aiError: string
  aiAnalysis: { action: string; data: Record<string, unknown> } | null
  handleAIAction: (action: string) => void
  clearAiResult: () => void
}

export function useAlertAI(alert: AlertResponse | undefined): AlertAIState {
  const [aiAnalysis, setAiAnalysis] = useState<{ action: string; data: Record<string, unknown> } | null>(null)
  const [aiLoading, setAiLoading] = useState(false)
  const [aiLoadingHint, setAiLoadingHint] = useState('🤖 AI分析中...')
  const [aiError, setAiError] = useState('')

  const handleAIAction = async (action: string) => {
    if (!alert) return
    setAiLoading(true)
    setAiLoadingHint('🤖 正在提交任务…')
    setAiError('')
    setAiAnalysis(null)

    try {
      const endpoint = {
        analyze: `/alerts/${alert.id}/analyze`,
        polish: `/alerts/${alert.id}/polish`,
        suggest: `/alerts/${alert.id}/suggest-actions`,
        impact: `/alerts/${alert.id}/predict-impact`,
      }[action] as string

      const { task_id } = await apiClient.submitAlertAiTask(endpoint, {})
      const task = await apiClient.pollAiTask(task_id, {
        onStatus: (status) => {
          setAiLoadingHint(STATUS_LABEL[status] || '🤖 AI分析中...')
        },
      })
      if (!task.result) {
        throw new Error('AI任务未返回结果')
      }
      setAiAnalysis({ action, data: task.result })
    } catch (err: unknown) {
      setAiError(formatAiError(err))
    } finally {
      setAiLoading(false)
      setAiLoadingHint('🤖 AI分析中...')
    }
  }

  return {
    aiLoading,
    aiLoadingHint,
    aiError,
    aiAnalysis,
    handleAIAction,
    clearAiResult: () => {
      setAiAnalysis(null)
      setAiError('')
    },
  }
}

/** 顶栏 AI 下拉按钮 */
export function AIActionsButton({
  aiLoading,
  onAction,
}: {
  aiLoading: boolean
  onAction: (action: string) => void
}) {
  return (
    <div className="relative group">
      <button
        type="button"
        className="px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600"
      >
        🤖 AI
      </button>
      <div className="absolute right-0 mt-1 w-40 bg-white rounded-lg shadow-lg border hidden group-hover:block z-20">
        <button
          type="button"
          onClick={() => onAction('analyze')}
          disabled={aiLoading}
          className="w-full px-4 py-2 text-left hover:bg-gray-50 text-sm rounded-t-lg disabled:opacity-50"
        >
          🔍 根因分析
        </button>
        <button
          type="button"
          onClick={() => onAction('polish')}
          disabled={aiLoading}
          className="w-full px-4 py-2 text-left hover:bg-gray-50 text-sm disabled:opacity-50"
        >
          ✨ 内容润色
        </button>
        <button
          type="button"
          onClick={() => onAction('suggest')}
          disabled={aiLoading}
          className="w-full px-4 py-2 text-left hover:bg-gray-50 text-sm disabled:opacity-50"
        >
          💡 建议操作
        </button>
        <button
          type="button"
          onClick={() => onAction('impact')}
          disabled={aiLoading}
          className="w-full px-4 py-2 text-left hover:bg-gray-50 text-sm rounded-b-lg disabled:opacity-50"
        >
          📊 影响预测
        </button>
      </div>
    </div>
  )
}

/** 顶栏下方整行 AI 结果卡片 */
export function AIAnalysisPanel({
  aiLoading,
  aiLoadingHint,
  aiError,
  aiAnalysis,
  onClose,
}: Pick<AlertAIState, 'aiLoading' | 'aiLoadingHint' | 'aiError' | 'aiAnalysis'> & {
  onClose: () => void
}) {
  if (!aiLoading && !aiError && !aiAnalysis) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="flex items-center justify-between px-6 py-3 border-b bg-gray-50/80">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
          AI 分析
        </h2>
        {(aiAnalysis || aiError) && !aiLoading && (
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            关闭
          </button>
        )}
      </div>

      <div className="p-6">
        {aiLoading && (
          <div className="text-center py-8">
            <div className="text-purple-600 animate-pulse">{aiLoadingHint}</div>
          </div>
        )}

        {aiError && !aiLoading && (
          <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-red-700 text-sm">
            {aiError}
          </div>
        )}

        {aiAnalysis && !aiLoading && (
          <>
            <h3 className="text-base font-medium text-gray-900 mb-4">
              {ACTION_TITLE[aiAnalysis.action] || 'AI 结果'}
            </h3>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
              <AIContentRenderer
                content={String(
                  aiAnalysis.data.analysis
                    || aiAnalysis.data.polished_content
                    || aiAnalysis.data.predicted_impact
                    || aiAnalysis.data.suggestion_content
                    || '',
                )}
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function formatAiError(err: unknown): string {
  if (err instanceof Error && err.message && !axios.isAxiosError(err)) {
    return err.message
  }
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (detail) return formatApiDetail(detail)
    if (err.message) return err.message
  }
  return 'AI请求失败'
}

function formatApiDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: string }).msg)
        return JSON.stringify(item)
      })
      .join('; ')
  }
  return ''
}
