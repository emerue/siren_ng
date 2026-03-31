import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getActiveIncidents, getIncidents, getZoneStats, getHistoricalIncidents } from '../api'
import type { Incident } from '../types'
import Nav from '../components/Nav'
import { formatDistanceToNow } from 'date-fns'


const ZONES = ['Lagos Island', 'Surulere', 'Ikeja', 'Lekki', 'Victoria Island', 'Oshodi', 'Yaba', 'Apapa']

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: 'bg-red-600 text-white',
  HIGH: 'bg-red-100 text-red-700',
  MEDIUM: 'bg-amber-100 text-amber-700',
  LOW: 'bg-yellow-100 text-yellow-700',
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    VERIFIED: 'bg-blue-100 text-blue-800',
    RESPONDING: 'bg-green-100 text-green-800',
    VERIFYING: 'bg-yellow-100 text-amber-700',
    RESOLVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-gray-100 text-gray-500',
    AGENCY_NOTIFIED: 'bg-purple-100 text-purple-800',
  }
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${map[status] || 'bg-gray-100 text-gray-500'}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

const TYPE_ICON: Record<string, string> = {
  FIRE: '🔥', FLOOD: '🌊', COLLAPSE: '🏚', RTA: '🚗',
  EXPLOSION: '💥', DROWNING: '🆘', HAZARD: '⚡',
}

export default function HomePage() {
  const { data: activeIncidents = [] } = useQuery<Incident[]>({
    queryKey: ['active-incidents'],
    queryFn: getActiveIncidents,
    refetchInterval: 60_000,
  })

  const { data: resolvedData } = useQuery({
    queryKey: ['resolved-incidents'],
    queryFn: () => getIncidents({ status: 'RESOLVED', page_size: '5' }),
    refetchInterval: 60_000,
  })
  const resolved: Incident[] = resolvedData?.results || []

  // Zone historical counts — powers the "Documented since 2010" line per zone card
  const { data: zoneStats = {} } = useQuery<Record<string, number>>({
    queryKey: ['zone-stats'],
    queryFn: getZoneStats,
    staleTime: 10 * 60 * 1000,
  })

  // A few historical entries to mix into the resolved ticker
  const { data: histData } = useQuery({
    queryKey: ['home-historical'],
    queryFn: () => getHistoricalIncidents({ page_size: '4' }),
    staleTime: 10 * 60 * 1000,
  })
  const historicalEntries: Incident[] = histData?.results || []

  return (
    <div className="min-h-screen bg-bg font-sans">
      <Nav />

      {/* Hero */}
      <section className="relative bg-gradient-to-br from-gray-900 via-slate-800 to-gray-900 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-5">
          <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(circle at 25% 25%, white 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        </div>
        <div className="relative max-w-4xl mx-auto py-20 px-6 text-center">
          {activeIncidents.length > 0 && (
            <div className="inline-flex items-center gap-2 bg-white/15 border border-white/20 rounded-full px-4 py-1.5 text-sm mb-6">
              <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
              <span className="font-medium">{activeIncidents.length} active emergency{activeIncidents.length !== 1 ? 's' : ''} in Lagos right now</span>
            </div>
          )}
          <h1 className="text-4xl sm:text-5xl font-bold mb-4 leading-tight">
            Protect the people<br />you love.
          </h1>
          <p className="text-white/85 text-lg mb-10 max-w-xl mx-auto leading-relaxed">
            Get instant alerts when emergencies happen near your home, your children's school, or anywhere your family is.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/watch"
              className="flex items-center justify-center gap-2.5 bg-white text-primary font-bold px-8 py-3.5 rounded-xl hover:bg-gray-100 transition shadow-lg text-base"
            >
              Watch a location
            </Link>
            <Link
              to="/report"
              className="flex items-center justify-center gap-2.5 border-2 border-white/60 text-white font-semibold px-8 py-3.5 rounded-xl hover:bg-white/10 transition text-base"
            >
              Report an incident
            </Link>
          </div>
          <p className="text-white/50 text-xs mt-6">No account required · AI-verified in ~90 seconds · Free forever</p>
        </div>
      </section>

      {/* Live active incidents bar */}
      {activeIncidents.length > 0 && (
        <section className="bg-red-50 border-b border-red-100 py-3 px-6">
          <div className="max-w-6xl mx-auto flex items-center gap-3 overflow-x-auto scrollbar-hide">
            <span className="text-xs font-bold text-red-600 uppercase tracking-wide shrink-0">Live</span>
            {activeIncidents.slice(0, 6).map((inc) => (
              <Link
                key={inc.id}
                to={`/track/${inc.id}`}
                className={`shrink-0 flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-full border ${SEVERITY_COLOR[inc.severity] || 'bg-white text-textBody border-border'}`}
              >
                <span>{TYPE_ICON[inc.incident_type] || '🚨'}</span>
                <span>{inc.incident_type} · {inc.zone_name || 'Lagos'}</span>
              </Link>
            ))}
            {activeIncidents.length > 6 && (
              <Link to="/feed" className="shrink-0 text-xs text-primary font-semibold hover:underline">
                +{activeIncidents.length - 6} more →
              </Link>
            )}
          </div>
        </section>
      )}

      {/* How it works — ICP focused */}
      <section className="py-12 px-6 bg-white border-y border-border">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center text-textPrimary mb-2">How Siren protects your family</h2>
          <p className="text-textBody text-center text-sm mb-10">Save locations once. We do the rest.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              { step: '1', icon: '📍', title: "Save your family's locations", desc: 'Home, school, work, family compound — add any place you care about. No account needed.' },
              { step: '2', icon: '🛡️', title: 'We watch for verified threats', desc: 'Our AI filters false reports 24/7. Only confirmed emergencies near your locations trigger an alert.' },
              { step: '3', icon: '🔔', title: 'You get an instant alert', desc: 'Email or WhatsApp — your choice. Full details: what happened, where, who is responding.' },
            ].map((item) => (
              <div key={item.step} className="relative text-center p-6 bg-gray-50 rounded-2xl border border-border">
                <div className="w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold mx-auto mb-4">
                  {item.step}
                </div>
                <div className="text-4xl mb-3">{item.icon}</div>
                <h3 className="font-semibold text-textPrimary mb-2">{item.title}</h3>
                <p className="text-textBody text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Lagos zones */}
      <section className="py-12 px-6 max-w-5xl mx-auto">
        <h2 className="text-xl font-bold mb-5 text-textPrimary">Active Zones</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {ZONES.map((zone) => {
            const count = activeIncidents.filter(i => i.zone_name?.toLowerCase().includes(zone.toLowerCase())).length
            // Sum historical from all matching zone stat keys
            const histCount = Object.entries(zoneStats)
              .filter(([k]) => k.toLowerCase().includes(zone.toLowerCase()) || zone.toLowerCase().includes(k.toLowerCase()))
              .reduce((sum, [, v]) => sum + v, 0)
            return (
              <Link
                key={zone}
                to={`/feed?zone_name=${encodeURIComponent(zone)}`}
                className="bg-white border border-border rounded-xl p-4 hover:border-primary hover:shadow-sm transition"
              >
                <div className="font-semibold text-textPrimary text-sm">{zone}</div>
                {count > 0
                  ? <div className="text-xs text-primary font-medium mt-1">{count} active 🔴</div>
                  : <div className="text-xs text-green-600 mt-1">All clear ✓</div>
                }
                {histCount > 0 && (
                  <div className="text-xs text-gray-400 mt-1">
                    Documented since 2010: {histCount}
                  </div>
                )}
              </Link>
            )
          })}
        </div>
      </section>

      {/* Recently resolved + historical entries */}
      {(resolved.length > 0 || historicalEntries.length > 0) && (
        <section className="py-8 px-6 max-w-5xl mx-auto">
          <h2 className="text-xl font-bold mb-5 text-textPrimary">Recently Resolved</h2>
          <div className="space-y-2.5">
            {resolved.map((inc) => (
              <Link
                key={inc.id}
                to={`/track/${inc.id}`}
                className="flex items-center gap-3 bg-white border border-border rounded-xl p-4 hover:border-primary hover:shadow-sm transition"
              >
                <span className="text-xl">{TYPE_ICON[inc.incident_type] || '🚨'}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-textPrimary text-sm">{inc.incident_type} — {inc.zone_name}</p>
                  <p className="text-xs text-textMuted mt-0.5">
                    {inc.resolved_at ? formatDistanceToNow(new Date(inc.resolved_at), { addSuffix: true }) : ''}
                    {inc.total_donations_naira > 0 && ` · ₦${inc.total_donations_naira.toLocaleString()} raised`}
                  </p>
                </div>
                <StatusBadge status={inc.status} />
              </Link>
            ))}

            {/* Historical entries — grey left border, no donations */}
            {historicalEntries.map((inc) => (
              <div
                key={`h-${inc.id}`}
                className="flex items-center gap-3 bg-gray-50 rounded-xl p-4"
                style={{ borderLeft: '3px solid #9CA3AF', border: '1px solid #E5E7EB', borderLeftWidth: '3px', borderLeftColor: '#9CA3AF', borderLeftStyle: 'solid' }}
              >
                <span className="text-xl opacity-60">{TYPE_ICON[inc.incident_type] || '🚨'}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-700 text-sm">{inc.incident_type} — {inc.zone_name}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(inc.created_at).toLocaleDateString('en-NG', { month: 'long', year: 'numeric' })}
                  </p>
                </div>
                <span className="text-xs font-medium px-2 py-0.5 rounded" style={{ background: '#E5E7EB', color: '#6B7280' }}>
                  HISTORICAL
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Join CTAs */}
      <section className="py-14 px-6 bg-white border-t border-border">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold mb-8 text-textPrimary text-center">Want to help respond?</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="border border-border rounded-2xl p-6">
              <div className="text-3xl mb-3">🩺</div>
              <h3 className="font-bold text-lg mb-2">Become a Community Responder</h3>
              <p className="text-textBody text-sm mb-4 leading-relaxed">
                Nurse, doctor, engineer, or trained in first aid? Register to receive GPS-guided alerts when emergencies happen near you.
              </p>
              <Link to="/join" className="block text-center bg-primary text-white px-4 py-2.5 rounded-xl text-sm font-semibold hover:bg-red-700 transition">
                Register as Responder →
              </Link>
            </div>
            <div className="border border-border rounded-2xl p-6">
              <div className="text-3xl mb-3">🏥</div>
              <h3 className="font-bold text-lg mb-2">Register Your Organisation</h3>
              <p className="text-textBody text-sm mb-4 leading-relaxed">
                Hospitals, ambulance services, fire safety companies — get notified when incidents happen within your service radius.
              </p>
              <Link to="/join" className="block text-center bg-primary text-white px-4 py-2.5 rounded-xl text-sm font-semibold hover:bg-red-700 transition">
                Register Organisation →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-10 px-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-2 font-bold text-lg">
            <span>🚨</span> Siren.ng
          </div>
          <div className="flex flex-wrap justify-center gap-5 text-gray-400">
            <Link to="/map" className="hover:text-white transition">Live Map</Link>
            <Link to="/feed" className="hover:text-white transition">Feed</Link>
            <Link to="/connect" className="hover:text-white transition">Connect WhatsApp</Link>
            <Link to="/watch" className="hover:text-white transition">Watch</Link>
            <Link to="/join" className="hover:text-white transition">Join</Link>
            <Link to="/login" className="hover:text-white transition">Admin</Link>
          </div>
          <p className="text-gray-500 text-xs text-center">For Lagos. By the community.</p>
        </div>
      </footer>
    </div>
  )
}
