import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useAuthStore } from './store/authStore'

import HomePage from './pages/HomePage'
import MapPage from './pages/MapPage'
import FeedPage from './pages/FeedPage'
import TrackPage from './pages/TrackPage'
import ReportPage from './pages/ReportPage'
import JoinPage from './pages/JoinPage'
import WatchPage from './pages/WatchPage'
import DonatePage from './pages/DonatePage'
import DonateSuccessPage from './pages/DonateSuccessPage'
import OrgsPage from './pages/OrgsPage'
import LoginPage from './pages/LoginPage'
import DashboardHome from './pages/DashboardHome'
import DashboardAnalytics from './pages/DashboardAnalytics'
import DashboardResponders from './pages/DashboardResponders'
import DashboardOrgs from './pages/DashboardOrgs'
import DashboardSubscribers from './pages/DashboardSubscribers'
import DashboardDonations from './pages/DashboardDonations'
import DashboardIncidentDetail from './pages/DashboardIncidentDetail'
import MyImpactPage from './pages/MyImpactPage'
import ConnectPage from './pages/ConnectPage'
import GuardianModePage from './pages/GuardianModePage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

/**
 * React Router does not scroll to `#hash` targets on its own. Anchor links in
 * the nav/footer (e.g. /#how-it-works) rely on this. Honours reduced-motion.
 */
function ScrollToHash() {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (!hash) {
      window.scrollTo({ top: 0 })
      return
    }
    const el = document.querySelector(hash)
    if (!el) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
  }, [pathname, hash])

  return null
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ScrollToHash />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/feed" element={<FeedPage />} />
          <Route path="/track/:id" element={<TrackPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/join" element={<JoinPage />} />
          <Route path="/watch" element={<WatchPage />} />
          <Route path="/connect" element={<ConnectPage />} />
          <Route path="/whatsapp" element={<Navigate to="/connect" replace />} />
          <Route path="/donate/success" element={<DonateSuccessPage />} />
          <Route path="/donate/:id" element={<DonatePage />} />
          <Route path="/organisations" element={<OrgsPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/my-impact" element={<MyImpactPage />} />
          <Route path="/guardian" element={<GuardianModePage />} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardHome /></ProtectedRoute>} />
          <Route path="/dashboard/incidents/:id" element={<ProtectedRoute><DashboardIncidentDetail /></ProtectedRoute>} />
          <Route path="/dashboard/analytics" element={<ProtectedRoute><DashboardAnalytics /></ProtectedRoute>} />
          <Route path="/dashboard/responders" element={<ProtectedRoute><DashboardResponders /></ProtectedRoute>} />
          <Route path="/dashboard/organisations" element={<ProtectedRoute><DashboardOrgs /></ProtectedRoute>} />
          <Route path="/dashboard/subscribers" element={<ProtectedRoute><DashboardSubscribers /></ProtectedRoute>} />
          <Route path="/dashboard/donations" element={<ProtectedRoute><DashboardDonations /></ProtectedRoute>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
