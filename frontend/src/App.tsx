import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/auth-store'
import { LoginPage } from './pages/login'
import { RegisterPage } from './pages/register'
import { Layout } from './components/layout/Layout'
import { AlertsPage } from './pages/alerts'
import { AlertDetailPage } from './pages/alerts/detail'
import { AlertSourcesPage } from './pages/alerts/sources'
import { RulesPage } from './pages/rules'
import { DedupRulesPage } from './pages/rules/dedup'
import { SuppressRulesPage } from './pages/rules/suppress'
import { AggregateRulesPage } from './pages/rules/aggregate'
import { ChannelsPage } from './pages/channels'
import { DiagnosePage } from './pages/diagnose'
import { SettingsPage } from './pages/settings'
import { CloudMetricsPage } from './pages/cloud-metrics'
import { TemplatesPage } from './pages/templates'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
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
        <Route path="rules/dedup" element={<DedupRulesPage />} />
        <Route path="rules/suppress" element={<SuppressRulesPage />} />
        <Route path="rules/aggregate" element={<AggregateRulesPage />} />
        <Route path="channels" element={<ChannelsPage />} />
        <Route path="diagnose" element={<DiagnosePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="cloud-metrics" element={<CloudMetricsPage />} />
        <Route path="templates" element={<TemplatesPage />} />
      </Route>
    </Routes>
  )
}

export default App
