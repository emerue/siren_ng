import { Link, useLocation } from 'react-router-dom'
import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { useFeatures } from '../hooks/useFeatures'

// Add `feature: '<flag>'` to any link to gate it behind a v8 feature flag.
// Links without a `feature` always show. Flags come from GET /api/features/.
const NAV_LINKS: { to: string; label: string; feature?: string }[] = [
  { to: '/',         label: 'Home' },
  { to: '/map',      label: 'Map' },
  { to: '/feed',     label: 'Feed' },
  { to: '/guardian', label: 'Guardian', feature: 'guardian_web' },
  { to: '/watch',    label: 'Watch' },
  { to: '/join',     label: 'Join' },
]

export default function Nav() {
  const location = useLocation()
  const token = useAuthStore((s) => s.token)
  const [open, setOpen] = useState(false)
  const { isOn } = useFeatures()
  const navLinks = NAV_LINKS.filter((l) => !l.feature || isOn(l.feature))

  const active = (path: string) =>
    (path === '/' ? location.pathname === '/' : location.pathname.startsWith(path))
      ? 'bg-red-50 text-primary font-semibold'
      : 'text-textBody hover:text-primary hover:bg-gray-50'

  return (
    <nav className="bg-white border-b border-border sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-6 py-3.5 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold text-primary">Siren.ng</Link>

        {/* Desktop */}
        <div className="hidden md:flex items-center gap-1 text-sm font-medium">
          {navLinks.map(({ to, label }) => (
            <Link key={to} to={to} className={`px-3 py-2 rounded-lg transition ${active(to)}`}>
              {label}
            </Link>
          ))}
          <Link to="/connect" className="ml-2 px-3 py-2 rounded-lg text-green-700 hover:bg-green-50 transition">
            Connect WhatsApp
          </Link>
          {token && (
            <Link to="/dashboard" className="ml-1 px-3 py-2 rounded-lg text-textMuted hover:text-primary hover:bg-gray-50 transition">
              Dashboard
            </Link>
          )}
          <Link to="/report" className="ml-3 bg-primary text-white px-4 py-2 rounded-lg hover:bg-red-700 transition font-semibold">
            Report
          </Link>
        </div>

        {/* Mobile */}
        <div className="md:hidden flex items-center gap-2">
          <Link to="/report" className="bg-primary text-white px-3 py-1.5 rounded-lg text-sm font-semibold">
            Report
          </Link>
          <button
            onClick={() => setOpen(!open)}
            className="w-9 h-9 flex flex-col items-center justify-center gap-1.5 rounded-lg hover:bg-gray-100 transition"
            aria-label="Menu"
          >
            <span className="block h-0.5 w-5 bg-gray-600 transition-all" />
            <span className="block h-0.5 w-5 bg-gray-600 transition-all" />
            <span className="block h-0.5 w-5 bg-gray-600 transition-all" />
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="md:hidden border-t border-border bg-white px-6 py-4 space-y-1">
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              onClick={() => setOpen(false)}
              className="block px-3 py-2.5 rounded-lg text-textBody hover:bg-gray-50 hover:text-primary font-medium transition"
            >
              {label}
            </Link>
          ))}
          <Link to="/connect" onClick={() => setOpen(false)} className="block px-3 py-2.5 rounded-lg text-green-700 hover:bg-green-50 font-medium transition">
            Connect WhatsApp
          </Link>
          {token && (
            <Link to="/dashboard" onClick={() => setOpen(false)} className="block px-3 py-2.5 rounded-lg text-textMuted hover:bg-gray-50 font-medium transition">
              Dashboard
            </Link>
          )}
        </div>
      )}
    </nav>
  )
}
