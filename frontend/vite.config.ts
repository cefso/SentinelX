import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { readFileSync } from 'fs'

// Vite 配置
// 重要: Docker 环境中前端通过 nginx 代理访问后端
// 本地开发时如果不用 Docker，代理目标为 http://localhost:8001

// 本地开发: 不使用 Docker 时默认代理到 http://localhost:8001
// Docker 部署: 由 nginx.conf 代理到 http://backend:8000
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8001'

// 读取 build-info.json
const buildInfoPath = path.resolve(__dirname, 'public/build-info.json')
let buildInfo = { git_commit: 'unknown', build_id: '', build_time: '' }
try {
  buildInfo = JSON.parse(readFileSync(buildInfoPath, 'utf-8'))
} catch (e) {
  // 构建时文件不存在是正常的，使用默认值
}

export default defineConfig({
  plugins: [react()],
  define: {
    // 注入构建信息，前端代码通过 __BUILD_INFO__ 访问
    '__BUILD_INFO__': JSON.stringify(buildInfo),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      '/health': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
})
