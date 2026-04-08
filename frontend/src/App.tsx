import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/auth-store'
import { LoginPage } from './pages/login'
import { RegisterPage } from './pages/register'
import { Layout } from './components/layout/Layout'
import { AlertsPage } from './pages/alerts'
import { AlertDetailPage } from './pages/alerts/detail'
import { AlertSourcesPage } from './pages/alerts/sources'
import { RulesPage } from './pages/rules'
import { ChannelsPage } from './pages/channels'
import { DiagnosePage } from './pages/diagnose'
import { SettingsPage } from './pages/settings'
import { AdminUsersPage } from './pages/admin/users'
import { CloudMetricsPage } from './pages/cloud-metrics'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function SystemAdminRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (user?.is_system !== true) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center p-8 bg-white rounded-lg shadow">
          <div className="text-5xl mb-4">🔒</div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">访问受限</h2>
          <p className="text-gray-500 mb-4">此页面仅系统管理员可访问</p>
          <Navigate to="/alerts" replace />
        </div>
      </div>
    )
  }

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/alerts" replace />} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="alerts/sources" element={<AlertSourcesPage />} />
        <Route path="alerts/:id" element={<AlertDetailPage />} />
        <Route path="rules" element={<RulesPage />} />
        <Route path="channels" element={<ChannelsPage />} />
        <Route path="diagnose" element={<DiagnosePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="cloud-metrics" element={<CloudMetricsPage />} />
        <Route path="admin/users" element={
          <SystemAdminRoute>
            <AdminUsersPage />
          </SystemAdminRoute>
        } />
      </Route>
    </Routes>
  )
}

export default App
