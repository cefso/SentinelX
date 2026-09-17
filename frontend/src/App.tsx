import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/auth-store'
import { LoginPage } from './pages/login'
import { RegisterPage } from './pages/register'
import { Layout } from './components/layout/Layout'

// 路由级 code splitting：按需加载各业务页面
const DashboardPage = lazy(() =>
  import('./pages/dashboard').then((m) => ({ default: m.DashboardPage }))
)
const AlertsPage = lazy(() =>
  import('./pages/alerts').then((m) => ({ default: m.AlertsPage }))
)
const AlertDetailPage = lazy(() =>
  import('./pages/alerts/detail').then((m) => ({ default: m.AlertDetailPage }))
)
const AlertSourcesPage = lazy(() =>
  import('./pages/alerts/sources').then((m) => ({ default: m.AlertSourcesPage }))
)
const UnresolvedAlertsPage = lazy(() =>
  import('./pages/alerts/unresolved').then((m) => ({ default: m.UnresolvedAlertsPage }))
)
const AlertHistoryPage = lazy(() =>
  import('./pages/alerts/history').then((m) => ({ default: m.AlertHistoryPage }))
)
const AlertsByInstancePage = lazy(() =>
  import('./pages/alerts/by-instance').then((m) => ({ default: m.AlertsByInstancePage }))
)
const AlertsByInstanceDetailPage = lazy(() =>
  import('./pages/alerts/by-instance/detail').then((m) => ({ default: m.AlertsByInstanceDetailPage }))
)
const RulesPage = lazy(() =>
  import('./pages/rules').then((m) => ({ default: m.RulesPage }))
)
const DedupRulesPage = lazy(() =>
  import('./pages/rules/dedup').then((m) => ({ default: m.DedupRulesPage }))
)
const SuppressRulesPage = lazy(() =>
  import('./pages/rules/suppress').then((m) => ({ default: m.SuppressRulesPage }))
)
const AggregateRulesPage = lazy(() =>
  import('./pages/rules/aggregate').then((m) => ({ default: m.AggregateRulesPage }))
)
const ChannelsPage = lazy(() =>
  import('./pages/channels').then((m) => ({ default: m.ChannelsPage }))
)
const DiagnosePage = lazy(() =>
  import('./pages/diagnose').then((m) => ({ default: m.DiagnosePage }))
)
const SettingsPage = lazy(() =>
  import('./pages/settings').then((m) => ({ default: m.SettingsPage }))
)
const CloudMetricsPage = lazy(() =>
  import('./pages/cloud-metrics').then((m) => ({ default: m.CloudMetricsPage }))
)
const TemplatesPage = lazy(() =>
  import('./pages/templates').then((m) => ({ default: m.TemplatesPage }))
)

function RouteFallback() {
  return (
    <div className="flex h-64 w-full items-center justify-center">
      <div className="flex flex-col items-center gap-3 text-muted-foreground">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-sm">加载中…</span>
      </div>
    </div>
  )
}

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
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route
          path="dashboard"
          element={
            <Suspense fallback={<RouteFallback />}>
              <DashboardPage />
            </Suspense>
          }
        />
        <Route
          path="alerts"
          element={
            <Suspense fallback={<RouteFallback />}>
              <AlertsPage />
            </Suspense>
          }
        />
        <Route
          path="alerts/unresolved"
          element={
            <Suspense fallback={<RouteFallback />}>
              <UnresolvedAlertsPage />
            </Suspense>
          }
        />
        <Route
          path="alerts/sources"
          element={
            <Suspense fallback={<RouteFallback />}>
              <AlertSourcesPage />
            </Suspense>
          }
        />
        <Route
          path="alerts/history"
          element={
            <Suspense fallback={<RouteFallback />}>
              <AlertHistoryPage />
            </Suspense>
          }
        />
        <Route
          path="alerts/:id"
          element={
            <Suspense fallback={<RouteFallback />}>
              <AlertDetailPage />
            </Suspense>
          }
        />
        <Route
          path="instance/alerts"
          element={
            <Suspense fallback={<RouteFallback />}>
              <AlertsByInstancePage />
            </Suspense>
          }
        />
        <Route
          path="instance/alerts/detail"
          element={
            <Suspense fallback={<RouteFallback />}>
              <AlertsByInstanceDetailPage />
            </Suspense>
          }
        />
        <Route
          path="rules"
          element={
            <Suspense fallback={<RouteFallback />}>
              <RulesPage />
            </Suspense>
          }
        />
        <Route
          path="rules/dedup"
          element={
            <Suspense fallback={<RouteFallback />}>
              <DedupRulesPage />
            </Suspense>
          }
        />
        <Route
          path="rules/suppress"
          element={
            <Suspense fallback={<RouteFallback />}>
              <SuppressRulesPage />
            </Suspense>
          }
        />
        <Route
          path="rules/aggregate"
          element={
            <Suspense fallback={<RouteFallback />}>
              <AggregateRulesPage />
            </Suspense>
          }
        />
        <Route
          path="channels"
          element={
            <Suspense fallback={<RouteFallback />}>
              <ChannelsPage />
            </Suspense>
          }
        />
        <Route
          path="diagnose"
          element={
            <Suspense fallback={<RouteFallback />}>
              <DiagnosePage />
            </Suspense>
          }
        />
        <Route
          path="settings"
          element={
            <Suspense fallback={<RouteFallback />}>
              <SettingsPage />
            </Suspense>
          }
        />
        <Route
          path="cloud-metrics"
          element={
            <Suspense fallback={<RouteFallback />}>
              <CloudMetricsPage />
            </Suspense>
          }
        />
        <Route
          path="templates"
          element={
            <Suspense fallback={<RouteFallback />}>
              <TemplatesPage />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  )
}

export default App
