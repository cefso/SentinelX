import { useBuildStore } from '@/stores/build-store'

export function BuildInfo() {
  const { frontendBuildId, backendBuildId, backendVersion } = useBuildStore()

  const frontendGit = frontendBuildId?.split('-')[0]
  const backendGit = backendBuildId?.split('-')[0]

  if (!frontendGit && !backendGit) return null

  return (
    <div className="text-xs text-gray-400 flex gap-4">
      {frontendGit && <span>前端: {frontendGit}</span>}
      {backendGit && <span>后端: {backendGit}</span>}
      {backendVersion && <span>v{backendVersion}</span>}
    </div>
  )
}
