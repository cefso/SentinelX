import { useEffect } from 'react'
import { useBuildStore } from '@/stores/build-store'
import { Check, X } from 'lucide-react'

export function AboutTab() {
  const {
    frontendBuildId, frontendBuildTime,
    backendVersion, backendBuildId, backendBuildTime,
    setBackendInfo,
  } = useBuildStore()

  // 获取后端版本信息
  useEffect(() => {
    const fetchBuildInfo = async () => {
      try {
        // 使用相对路径，Docker环境下nginx已配置/health/代理到backend
        // Vite开发模式下需要配置代理到localhost:8001
        const response = await fetch(`/health/build`)
        if (response.ok) {
          const data = await response.json()
          setBackendInfo(
            data.git_commit || 'unknown',
            data.version || 'unknown',
            data.build_id || 'unknown',
            data.build_time || '',
          )
        }
      } catch (err) {
        console.error('Failed to fetch backend build info:', err)
      }
    }
    if (!backendBuildId) {
      fetchBuildInfo()
    }
  }, [backendBuildId, setBackendInfo])

  // Build ID 格式: <git-short>-<timestamp>，取前缀比较 commit 一致性
  const frontendGit = frontendBuildId?.split('-')[0]
  const backendGit = backendBuildId?.split('-')[0]
  const versionMatch = frontendGit && backendGit && frontendGit !== 'unknown' && backendGit !== 'unknown' && frontendGit === backendGit
  const versionMismatch = frontendGit && backendGit && frontendGit !== backendGit

  // 格式化 Build ID: "a1b2c3d-20260417-061552" → "a1b2c3d @ 2026-04-17 06:15"
  function formatBuildId(buildId: string | null, buildTime: string | null): string {
    if (!buildId) return '-'
    const git = buildId.split('-')[0]
    if (buildTime) {
      // ISO 格式: "2026-04-17T06:15:52Z" → "2026-04-17 06:15"
      const t = buildTime.replace('T', ' ').replace(/:\d{2}Z$/, '')
      return `${git} @ ${t}`
    }
    return buildId
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-medium mb-1">关于 SentinelX</h3>
      <p className="text-sm text-gray-500 mb-6">综合告警平台 - 版本与构建信息</p>

      <dl className="space-y-4">
        <div className="flex items-center justify-between py-3 border-b">
          <dt className="text-sm text-gray-500">应用名称</dt>
          <dd className="text-sm font-medium">SentinelX</dd>
        </div>
        <div className="flex items-center justify-between py-3 border-b">
          <dt className="text-sm text-gray-500">后端版本</dt>
          <dd className="text-sm font-medium">{backendVersion || '-'}</dd>
        </div>
        <div className="flex items-center justify-between py-3 border-b">
          <dt className="text-sm text-gray-500">前端构建</dt>
          <dd className="text-sm font-mono">{formatBuildId(frontendBuildId, frontendBuildTime)}</dd>
        </div>
        <div className="flex items-center justify-between py-3 border-b">
          <dt className="text-sm text-gray-500">后端构建</dt>
          <dd className="text-sm font-mono">{formatBuildId(backendBuildId, backendBuildTime)}</dd>
        </div>
        <div className="flex items-center justify-between py-3">
          <dt className="text-sm text-gray-500">一致性状态</dt>
          <dd className="text-sm">
            {versionMatch && (
              <span className="inline-flex items-center gap-1 text-green-600">
                <Check className="w-4 h-4" /> 版本一致
              </span>
            )}
            {versionMismatch && (
              <span className="inline-flex items-center gap-1 text-yellow-600">
                <X className="w-4 h-4" /> 版本不一致
              </span>
            )}
            {!frontendBuildId && !backendBuildId && (
              <span className="text-gray-400">加载中...</span>
            )}
          </dd>
        </div>
      </dl>

      <div className="mt-6 pt-6 border-t">
        <h4 className="text-sm font-medium mb-3">构建说明</h4>
        <div className="text-sm text-gray-500 space-y-2">
          <p>• 构建时自动从 <code className="px-1 py-0.5 bg-gray-100 rounded text-xs">.git</code> 读取当前 commit hash，写入 <code className="px-1 py-0.5 bg-gray-100 rounded text-xs">build-info.json</code></p>
          <p>• 前端：Vite 打包时将 <code className="px-1 py-0.5 bg-gray-100 rounded text-xs">build-info.json</code> 注入到产物中</p>
          <p>• 后端：启动时从磁盘读取 <code className="px-1 py-0.5 bg-gray-100 rounded text-xs">build-info.json</code></p>
          <p>• 版本一致：说明前后端代码来自同一 git commit</p>
        </div>
      </div>
    </div>
  )
}
