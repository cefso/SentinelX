import { create } from 'zustand'

const BUILD_INFO = JSON.parse(import.meta.env.VITE_BUILD_INFO || '{}')

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
