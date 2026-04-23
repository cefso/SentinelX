import { useState } from 'react'

export function Labels({
  labels,
  annotations,
}: {
  labels: Record<string, any>
  annotations: Record<string, any>
}) {
  const [showAllLabels, setShowAllLabels] = useState(false)
  const [showAllAnnotations, setShowAllAnnotations] = useState(false)

  const labelEntries = Object.entries(labels || {})
  const annotationEntries = Object.entries(annotations || {})
  const displayedLabels = showAllLabels ? labelEntries : labelEntries.slice(0, 5)
  const displayedAnnotations = showAllAnnotations ? annotationEntries : annotationEntries.slice(0, 5)

  return (
    <>
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
                <span className="font-mono ml-1">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
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
                <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
