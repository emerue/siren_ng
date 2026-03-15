import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getActiveIncidents, getIncidents } from '../api'
import type { Incident } from '../types'
import { formatDistanceToNow } from 'date-fns'

const WHATSAPP_NUMBER = import.meta.env.VITE_WHATSAPP_NUMBER || '+2349000000000'
const WA = WHATSAPP_NUMBER.replace('+', '')

const ZONES = ['Lagos Island', 'Surulere', 'Ikeja', 'Lekki', 'Victoria Island', 'Oshodi', 'Yaba', 'Apapa']

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    VERIFIED: 'bg-blue-100 text-blue-800',
    RESPONDING: 'bg-green-100 text-green-800',
    VERIFYING: 'bg-yellow-100 text-amber-700',
    RESOLVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-gray-100 text-gray-500',
  }
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${map[status] || 'bg-gray-100 text-gray-500'}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

const WA_FEATURES = [
  { icon: '🚨', text: 'Report emergency — send any description' },
  { icon: '📍', text: 'Save a watch location — type WATCH' },
  { icon: '🩺', text: 'Join as responder — type RESPONDER' },
  { icon: '🏥', text: 'Register organisation — type REGISTER ORG' },
  { icon: '✅', text: 'Vouch for incident — type VOUCH <id>' },
  { icon: '🔔', text: 'Manage alerts — type MY ALERTS' },
  { icon: '🛑', text: 'Stop alerts — type STOP <label>' },
]

const WEB_FEATURES = [
  { icon: '🚨', text: 'Report emergency with map pin + photos', link: '/report' },
  { icon: '📍', text: 'Save watch locations with radius control', link: '/watch' },
  { icon: '🩺', text: 'Join as responder via web form', link: '/join' },
  { icon: '🏥', text: 'Register organisation via web form', link: '/join' },
  { icon: '🗺️', text: 'Live map of all active incidents', link: '/map' },
  { icon: '📋', text: 'Browse & filter the incident feed', link: '/feed' },
  { icon: '💳', text: 'Donate to specific incidents', link: '/feed' },
]

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

  return (
    <div className="min-h-screen bg-bg font-sans">
      {/* Nav */}
      <nav className="bg-white border-b border-border px-6 py-4 flex items-center justify-between">
        <span className="text-xl font-bold text-primary">🚨 Siren.ng</span>
        <div className="flex gap-4 text-sm">
          <Link to="/map" className="text-textBody hover:text-primary">Map</Link>
          <Link to="/feed" className="text-textBody hover:text-primary">Feed</Link>
          <Link to="/watch" className="text-textBody hover:text-primary">Watch</Link>
          <Link to="/join" className="text-textBody hover:text-primary">Join</Link>
          <Link to="/orgs" className="text-textBody hover:text-primary">Orgs</Link>
          <Link to="/login" className="text-textBody hover:text-primary">Dashboard</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-primary text-white py-16 px-6 text-center">
        <div className="max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-white/20 rounded-full px-4 py-1 text-sm mb-4">
            <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
            {activeIncidents.length} active incident{activeIncidents.length !== 1 ? 's' : ''} right now
          </div>
          <h1 className="text-4xl font-bold mb-4">Lagos Emergency Coordination</h1>
          <p className="text-white/90 text-lg mb-8">
            Report emergencies, get community alerts, and coordinate response — via WhatsApp or the web app. No account required.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href={`https://wa.me/${WA}?text=Emergency`}
              className="flex items-center justify-center gap-2 bg-white text-primary font-semibold px-8 py-3 rounded-lg hover:bg-gray-100 transition"
            >
              <span className="text-xl">📱</span>
              <span>Use WhatsApp</span>
            </a>
            <Link
              to="/report"
              className="flex items-center justify-center gap-2 border-2 border-white text-white font-semibold px-8 py-3 rounded-lg hover:bg-white/10 transition"
            >
              <span className="text-xl">💻</span>
              <span>Use Web App</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Dual channel — choose your way */}
      <section className="py-14 px-6 max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-center mb-2 text-textPrimary">Two ways to use Siren.ng</h2>
        <p className="text-center text-textBody mb-10">
          Every feature is available on both channels. Use whichever works best for you.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* WhatsApp channel */}
          <div className="bg-white rounded-2xl border-2 border-green-200 p-8 flex flex-col">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-4xl">📱</span>
              <div>
                <h3 className="text-xl font-bold text-textPrimary">WhatsApp</h3>
                <p className="text-sm text-textMuted">No internet browser needed</p>
              </div>
            </div>
            <p className="text-textBody text-sm mb-6">
              Works on any phone with WhatsApp — even on slow 2G. Just send a message and follow the guided prompts. No forms, no clicks.
            </p>
            <ul className="space-y-3 mb-8 flex-1">
              {WA_FEATURES.map((f) => (
                <li key={f.text} className="flex items-start gap-2 text-sm text-textBody">
                  <span className="mt-0.5">{f.icon}</span>
                  <span>{f.text}</span>
                </li>
              ))}
            </ul>
            <a
              href={`https://wa.me/${WA}`}
              className="block text-center bg-green-600 text-white font-semibold px-6 py-3 rounded-xl hover:bg-green-700 transition"
            >
              Open WhatsApp Chat →
            </a>
            <p className="text-center text-xs text-textMuted mt-3">
              Save as contact: {WHATSAPP_NUMBER}
            </p>
          </div>

          {/* Web App channel */}
          <div className="bg-white rounded-2xl border-2 border-primary/30 p-8 flex flex-col">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-4xl">💻</span>
              <div>
                <h3 className="text-xl font-bold text-textPrimary">Web App</h3>
                <p className="text-sm text-textMuted">Rich interface, maps & media</p>
              </div>
            </div>
            <p className="text-textBody text-sm mb-6">
              Full interactive experience in your browser. Pin your location on a map, attach photos, see live incident updates, donate, and manage everything in one place.
            </p>
            <ul className="space-y-3 mb-8 flex-1">
              {WEB_FEATURES.map((f) => (
                <li key={f.text} className="flex items-start gap-2 text-sm text-textBody">
                  <span className="mt-0.5">{f.icon}</span>
                  <Link to={f.link} className="hover:text-primary hover:underline">{f.text}</Link>
                </li>
              ))}
            </ul>
            <Link
              to="/report"
              className="block text-center bg-primary text-white font-semibold px-6 py-3 rounded-xl hover:bg-red-700 transition"
            >
              Report an Emergency →
            </Link>
            <p className="text-center text-xs text-textMuted mt-3">
              No account needed for most features
            </p>
          </div>
        </div>

        {/* Quick WhatsApp commands reference */}
        <div className="mt-8 bg-green-50 border border-green-200 rounded-xl p-6">
          <h4 className="font-semibold text-textPrimary mb-3">WhatsApp quick commands</h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
            {[
              ['Emergency', 'Report an incident'],
              ['WATCH', 'Save a location for alerts'],
              ['RESPONDER', 'Join as community responder'],
              ['REGISTER ORG', 'Register your organisation'],
              ['MY ALERTS', 'View your active subscriptions'],
              ['VOUCH <id>', 'Confirm an incident is real'],
            ].map(([cmd, desc]) => (
              <a
                key={cmd}
                href={`https://wa.me/${WA}?text=${encodeURIComponent(cmd === 'Emergency' ? 'Emergency at [describe location]' : cmd)}`}
                className="flex flex-col bg-white border border-green-200 rounded-lg p-3 hover:border-green-500 transition"
              >
                <code className="font-mono font-bold text-green-700 text-xs">{cmd}</code>
                <span className="text-textMuted text-xs mt-0.5">{desc}</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-10 px-6 max-w-4xl mx-auto border-t border-border">
        <h2 className="text-2xl font-bold text-center mb-8 text-textPrimary">How it works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { step: '1', icon: '📣', title: 'Report', desc: 'Send one WhatsApp message or fill the web form. No account, no friction.' },
            { step: '2', icon: '🤖', title: 'AI Verifies in 90s', desc: 'Claude AI classifies and verifies the incident. Fraudulent reports are filtered out automatically.' },
            { step: '3', icon: '🚀', title: 'Community Responds', desc: 'Nearest qualified responders and registered organisations receive GPS-guided alerts immediately.' },
          ].map((item) => (
            <div key={item.step} className="bg-white rounded-xl p-6 border border-border text-center">
              <div className="text-4xl mb-3">{item.icon}</div>
              <h3 className="font-semibold text-textPrimary mb-2">{item.title}</h3>
              <p className="text-textBody text-sm">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Lagos zones */}
      <section className="py-8 px-6 max-w-4xl mx-auto">
        <h2 className="text-xl font-bold mb-4 text-textPrimary">Lagos Zones</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {ZONES.map((zone) => {
            const count = activeIncidents.filter(
              (i) => i.zone_name?.toLowerCase().includes(zone.toLowerCase())
            ).length
            return (
              <Link
                key={zone}
                to={`/feed?zone_name=${encodeURIComponent(zone)}`}
                className="bg-white border border-border rounded-lg p-3 hover:border-primary transition text-sm"
              >
                <div className="font-medium text-textPrimary">{zone}</div>
                {count > 0 && <div className="text-xs text-primary mt-1">{count} active</div>}
              </Link>
            )
          })}
        </div>
      </section>

      {/* Recently resolved */}
      {resolved.length > 0 && (
        <section className="py-8 px-6 max-w-4xl mx-auto">
          <h2 className="text-xl font-bold mb-4 text-textPrimary">Recently Resolved</h2>
          <div className="space-y-3">
            {resolved.map((inc) => (
              <Link
                key={inc.id}
                to={`/track/${inc.id}`}
                className="flex items-center justify-between bg-white border border-border rounded-lg p-4 hover:border-primary transition"
              >
                <div>
                  <span className="font-medium text-textPrimary">{inc.incident_type} — {inc.zone_name}</span>
                  <div className="text-xs text-textMuted mt-0.5">
                    {inc.resolved_at ? formatDistanceToNow(new Date(inc.resolved_at), { addSuffix: true }) : ''}
                    {inc.total_donations_naira > 0 && ` · ₦${inc.total_donations_naira.toLocaleString()} raised`}
                  </div>
                </div>
                <StatusBadge status={inc.status} />
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Join CTAs — dual channel */}
      <section className="py-12 px-6 bg-white border-t border-border">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-xl font-bold mb-6 text-textPrimary">Want to help respond?</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="border border-border rounded-xl p-6">
              <div className="text-3xl mb-3">🩺</div>
              <h3 className="font-bold text-lg mb-2">Become a Community Responder</h3>
              <p className="text-textBody text-sm mb-4">
                Nurse, doctor, engineer, or trained in first aid? Register to receive alerts when incidents happen near you.
              </p>
              <div className="flex gap-2">
                <a
                  href={`https://wa.me/${WA}?text=RESPONDER`}
                  className="flex-1 text-center border border-green-300 text-green-700 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-green-50 transition"
                >
                  📱 Via WhatsApp
                </a>
                <Link
                  to="/join"
                  className="flex-1 text-center bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 transition"
                >
                  💻 Via Web Form
                </Link>
              </div>
            </div>
            <div className="border border-border rounded-xl p-6">
              <div className="text-3xl mb-3">🏥</div>
              <h3 className="font-bold text-lg mb-2">Register Your Organisation</h3>
              <p className="text-textBody text-sm mb-4">
                Hospitals, ambulance services, fire safety companies — get notified when incidents happen near you.
              </p>
              <div className="flex gap-2">
                <a
                  href={`https://wa.me/${WA}?text=REGISTER+ORG`}
                  className="flex-1 text-center border border-green-300 text-green-700 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-green-50 transition"
                >
                  📱 Via WhatsApp
                </a>
                <Link
                  to="/join"
                  className="flex-1 text-center bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 transition"
                >
                  💻 Via Web Form
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
