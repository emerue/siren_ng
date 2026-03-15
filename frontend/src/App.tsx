import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/feed" element={<FeedPage />} />
          <Route path="/track/:id" element={<TrackPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/join" element={<JoinPage />} />
          <Route path="/watch" element={<WatchPage />} />
          <Route path="/donate/success" element={<DonateSuccessPage />} />
          <Route path="/donate/:id" element={<DonatePage />} />
          <Route path="/organisations" element={<OrgsPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/my-impact" element={<MyImpactPage />} />
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
