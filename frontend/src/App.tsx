import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/auth-store'
import { LoginPage } from './pages/login'
import { Layout } from './components/layout/Layout'
import { AlertsPage } from './pages/alerts'
import { AlertDetailPage } from './pages/alerts/detail'
import { RulesPage } from './pages/rules'
import { ChannelsPage } from './pages/channels'
import { DiagnosePage } from './pages/diagnose'
import { SettingsPage } from './pages/settings'

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
        <Route path="alerts/:id" element={<AlertDetailPage />} />
        <Route path="rules" element={<RulesPage />} />
        <Route path="channels" element={<ChannelsPage />} />
        <Route path="diagnose" element={<DiagnosePage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}

export default App
