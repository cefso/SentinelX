import { create } from 'zustand'

// 硬编码的内联版本信息（构建时通过打包工具注入）
const BUILD_INFO = __BUILD_INFO__

interface BuildState {
  frontendBuildId: string | null
  frontendBuildTime: string | null
  backendVersion: string | null
  backendBuildId: string | null
  backendBuildTime: string | null
  setBackendInfo: (commit: string, version: string, buildId: string, buildTime: string) => void
}

export const useBuildStore = create<BuildState>((set) => ({
  frontendBuildId: BUILD_INFO.build_id || 'unknown',
  frontendBuildTime: BUILD_INFO.build_time || '',
  backendVersion: null,
  backendBuildId: null,
  backendBuildTime: null,
  setBackendInfo: (_commit, version, buildId, buildTime) => set({
    backendVersion: version,
    backendBuildId: buildId,
    backendBuildTime: buildTime,
  }),
}))
