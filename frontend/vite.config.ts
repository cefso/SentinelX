import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Vite 配置
// 重要: Docker 环境中前端通过代理访问后端，代理目标是 http://sentinelx-backend:8000
// 本地开发时如果不用 Docker，需要将目标改为 http://localhost:8000

// 本地开发: 不使用 Docker 时设为 http://localhost:8000
// Docker 部署: 由 docker-compose.yml 设置为 http://sentinelx-backend:8000
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8001'

export default defineConfig({
  plugins: [react()],
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
    },
  },
})
