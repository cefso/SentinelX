import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Vite 配置
// 重要: Docker 环境中前端通过 nginx 代理访问后端
// 本地开发时如果不用 Docker，代理目标为 http://localhost:8001

// 本地开发: 不使用 Docker 时默认代理到 http://localhost:8001
// Docker 部署: 由 nginx.conf 代理到 http://backend:8000
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
