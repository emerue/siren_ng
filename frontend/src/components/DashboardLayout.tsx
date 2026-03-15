import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const NAV = [
  { to: '/dashboard', label: '🏠 Home' },
  { to: '/dashboard/analytics', label: '📊 Analytics' },
  { to: '/dashboard/responders', label: '👤 Responders' },
  { to: '/dashboard/organisations', label: '🏥 Organisations' },
  { to: '/dashboard/donations', label: '💰 Donations' },
  { to: '/dashboard/subscribers', label: '📍 Subscribers' },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const logout = useAuthStore((s) => s.logout)
  const username = useAuthStore((s) => s.username)
  const navigate = useNavigate()
  const location = useLocation()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-bg font-sans flex">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-border flex flex-col py-6 px-4 shrink-0">
        <Link to="/" className="font-bold text-primary text-lg mb-8 block">🚨 Siren.ng</Link>
        <nav className="flex-1 space-y-1">
          {NAV.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className={`block px-3 py-2 rounded-lg text-sm font-medium transition ${
                location.pathname === to
                  ? 'bg-red-50 text-primary'
                  : 'text-textBody hover:bg-gray-50 hover:text-primary'
              }`}
            >
              {label}
            </Link>
          ))}
        </nav>
        <div className="text-xs text-textMuted">
          <p className="mb-2">{username}</p>
          <button onClick={handleLogout} className="text-primary hover:underline">Logout</button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
