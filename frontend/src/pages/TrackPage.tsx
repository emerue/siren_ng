import { useState } from 'react'
import { useParams, Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import { formatDistanceToNow } from 'date-fns'
import { getIncident, getResources, getDonationSummary, vouchIncident, suggestResource, claimResource } from '../api'
import { useWebSocket } from '../hooks/useWebSocket'
import type { Incident, ResourceItem, DonationSummary } from '../types'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    VERIFIED: 'bg-blue-100 text-blue-800',
    RESPONDING: 'bg-green-100 text-green-800 animate-pulse',
    VERIFYING: 'bg-yellow-100 text-amber-700 animate-pulse',
    RESOLVED: 'bg-green-100 text-green-800',
    AGENCY_NOTIFIED: 'bg-purple-100 text-purple-800',
    DETECTED: 'bg-gray-100 text-gray-600',
    REJECTED: 'bg-gray-100 text-gray-400',
  }
  return (
    <span className={`inline-block text-sm font-bold px-3 py-1 rounded-full ${map[status] || 'bg-gray-100 text-gray-500'}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    CRITICAL: 'bg-red-600 text-white animate-pulse',
    HIGH: 'bg-red-600 text-white',
    MEDIUM: 'bg-amber-500 text-white',
    LOW: 'bg-yellow-300 text-gray-800',
  }
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded ${map[severity] || 'bg-gray-200 text-gray-600'}`}>
      {severity}
    </span>
  )
}

function ResourceStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    NEEDED: 'bg-red-100 text-red-700',
    CLAIMED: 'bg-amber-100 text-amber-700',
    ARRIVED: 'bg-green-100 text-green-700',
  }
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${map[status] || ''}`}>
      {status}
    </span>
  )
}

export default function TrackPage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const fromCommute = searchParams.get('from') === 'commute'
  const qc = useQueryClient()
  useWebSocket()

  const [showSuggestModal, setShowSuggestModal] = useState(false)
  const [showClaimModal, setShowClaimModal] = useState<string | null>(null)
  const [suggestForm, setSuggestForm] = useState({ category: 'OTHER', label: '', suggested_by_name: '' })
  const [claimForm, setClaimForm] = useState({ claimer_name: '', claimer_phone: '' })

  const { data: incident, isLoading } = useQuery<Incident>({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id!),
    refetchInterval: 30_000,
    enabled: !!id,
  })

  const { data: resources = [] } = useQuery<ResourceItem[]>({
    queryKey: ['resources', id],
    queryFn: () => getResources(id!),
    refetchInterval: 30_000,
    enabled: !!id && !!incident && ['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED'].includes(incident.status),
  })

  const { data: donationSummary } = useQuery<DonationSummary>({
    queryKey: ['donation-summary', id],
    queryFn: () => getDonationSummary(id!),
    refetchInterval: 30_000,
    enabled: !!id,
  })

  const vouchMut = useMutation({
    mutationFn: () => vouchIncident(id!, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incident', id] }),
  })

  const suggestMut = useMutation({
    mutationFn: (data: typeof suggestForm) =>
      suggestResource({ ...data, incident: id, session_hash: getSession() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['resources', id] })
      setShowSuggestModal(false)
      setSuggestForm({ category: 'OTHER', label: '', suggested_by_name: '' })
    },
  })

  const claimMut = useMutation({
    mutationFn: ({ resourceId, form }: { resourceId: string; form: typeof claimForm }) =>
      claimResource(resourceId, { ...form, session_hash: getSession() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['resources', id] })
      setShowClaimModal(null)
      setClaimForm({ claimer_name: '', claimer_phone: '' })
    },
  })

  function getSession(): string {
    let s = sessionStorage.getItem('siren_session')
    if (!s) { s = Math.random().toString(36).slice(2); sessionStorage.setItem('siren_session', s) }
    return s
  }

  if (isLoading) return <div className="flex items-center justify-center h-screen text-textMuted">Loading...</div>
  if (!incident) return <div className="flex items-center justify-center h-screen text-textMuted">Incident not found.</div>

  const showResourceBoard = ['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED'].includes(incident.status)

  return (
    <div className="min-h-screen bg-bg font-sans">
      {/* Header */}
      <div className="bg-primary text-white px-6 py-4 flex items-center justify-between">
        <Link to="/" className="font-bold text-lg">Siren.ng</Link>
        <span className="text-sm opacity-80">Your report is being tracked</span>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
        {/* Status */}
        <div className="bg-white rounded-xl border border-border p-6 text-center">
          <div className="text-4xl mb-3">
            {incident.status === 'RESOLVED' ? '✅' : incident.status === 'REJECTED' ? '❌' : '🚨'}
          </div>
          <StatusBadge status={incident.status} />
          <div className="mt-3 flex items-center justify-center gap-2">
            <SeverityBadge severity={incident.severity} />
            <span className="text-textBody text-sm">{incident.incident_type}</span>
            {incident.is_infrastructure && (
              <span className="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded uppercase">
                Infrastructure Hazard
              </span>
            )}
          </div>
          <p className="text-textMuted text-sm mt-2">{incident.zone_name || incident.address_text}</p>
          <p className="text-textMuted text-xs mt-1">
            {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}
          </p>
          <div className="flex gap-2 justify-center mt-4">
            <button
              onClick={() => vouchMut.mutate()}
              disabled={vouchMut.isPending}
              className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 disabled:opacity-50"
            >
              Vouch ({incident.vouch_count})
            </button>
            <button
              onClick={() => navigator.clipboard.writeText(window.location.href)}
              className="border border-border px-4 py-2 rounded-lg text-sm hover:border-primary"
            >
              Share
            </button>
          </div>
        </div>

        {fromCommute && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
            <p className="text-amber-800 font-semibold text-sm">
              This incident is on your saved commute route.
            </p>
          </div>
        )}

        {/* Description */}
        <div className="bg-white rounded-xl border border-border p-4">
          <h3 className="font-semibold text-textPrimary mb-2">Report</h3>
          <p className="text-textBody text-sm">{incident.description}</p>
        </div>

        {/* Map */}
        {incident.location_lat && incident.location_lng && (
          <div className="rounded-xl overflow-hidden border border-border" style={{ height: 220 }}>
            <MapContainer
              center={[incident.location_lat, incident.location_lng]}
              zoom={15}
              style={{ height: '100%', width: '100%' }}
              zoomControl={false}
            >
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Marker position={[incident.location_lat, incident.location_lng]}>
                <Popup>{incident.incident_type} — {incident.zone_name}</Popup>
              </Marker>
            </MapContainer>
          </div>
        )}

        {/* Response log */}
        {(incident.response_logs || []).length > 0 && (
          <div className="bg-white rounded-xl border border-border p-4">
            <h3 className="font-semibold text-textPrimary mb-3">Timeline</h3>
            <div className="space-y-3">
              {incident.response_logs!.map((log) => (
                <div key={log.id} className="flex gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-primary mt-1.5 flex-shrink-0"></div>
                  <div>
                    <span className="font-medium">{log.to_status.replace('_', ' ')}</span>
                    {log.note && <span className="text-textMuted"> — {log.note}</span>}
                    <div className="text-textMuted text-xs">
                      {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })} · {log.actor}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Resource board */}
        {showResourceBoard && (
          <div className="bg-white rounded-xl border border-border p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-textPrimary">Resource Board</h3>
              <button
                onClick={() => setShowSuggestModal(true)}
                className="text-primary text-sm font-semibold hover:underline"
              >
                + Add what you can bring
              </button>
            </div>
            {resources.length === 0 && (
              <p className="text-textMuted text-sm">No resources suggested yet. Be the first!</p>
            )}
            <div className="space-y-2">
              {resources.map((item) => (
                <div key={item.id} className="flex items-center justify-between border border-border rounded-lg p-3">
                  <div>
                    <span className={`font-medium text-sm ${item.status === 'ARRIVED' ? 'line-through text-textMuted' : 'text-textPrimary'}`}>
                      {item.label}
                    </span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <ResourceStatusBadge status={item.status} />
                      {item.claim_count > 0 && (
                        <span className="text-xs text-textMuted">{item.claim_count} people said they can bring it</span>
                      )}
                    </div>
                  </div>
                  {item.status !== 'ARRIVED' && (
                    <button
                      onClick={() => setShowClaimModal(item.id)}
                      className="text-xs bg-primary text-white px-3 py-1 rounded-lg hover:bg-red-700"
                    >
                      I can bring this
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Donations */}
        {showResourceBoard && (
          <div className="bg-white rounded-xl border border-border p-4">
            <h3 className="font-semibold text-textPrimary mb-1">Support this Incident</h3>
            {donationSummary && donationSummary.donation_count > 0 && (
              <p className="text-textMuted text-sm mb-3">
                &#8358;{donationSummary.total_naira.toLocaleString()} raised by {donationSummary.donation_count} donor{donationSummary.donation_count !== 1 ? 's' : ''}
              </p>
            )}
            <div className="grid grid-cols-1 gap-3">
              {[
                { fund: 'VICTIM', icon: '🏠', label: 'Victim Relief', desc: 'Help the affected family directly' },
                { fund: 'RESPONDER', icon: '👤', label: 'Responder Appreciation', desc: 'Thank the people who showed up' },
                { fund: 'PLATFORM', icon: '🚨', label: 'Emergency Response Fund', desc: 'Keep Siren running for the next emergency' },
              ].map((f) => (
                <Link
                  key={f.fund}
                  to={`/donate/${id}?fund=${f.fund}`}
                  className="flex items-center gap-3 border border-border rounded-lg p-3 hover:border-primary transition"
                >
                  <span className="text-2xl">{f.icon}</span>
                  <div>
                    <div className="font-medium text-textPrimary text-sm">{f.label}</div>
                    <div className="text-textMuted text-xs">{f.desc}</div>
                  </div>
                  <span className="ml-auto text-primary text-sm font-semibold">Donate →</span>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Suggest modal */}
      {showSuggestModal && (
        <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50">
          <div className="bg-white w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl p-6">
            <h3 className="font-bold text-lg mb-4">Suggest a Resource</h3>
            <select
              value={suggestForm.category}
              onChange={(e) => setSuggestForm((f) => ({ ...f, category: e.target.value }))}
              className="w-full border border-border rounded-lg p-2 mb-3 text-sm"
            >
              {['TRANSPORT', 'EQUIPMENT', 'MEDICAL', 'FOOD_WATER', 'MANPOWER', 'OTHER'].map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <input
              value={suggestForm.label}
              onChange={(e) => setSuggestForm((f) => ({ ...f, label: e.target.value }))}
              placeholder="What is needed? e.g. 6-foot ladder"
              className="w-full border border-border rounded-lg p-2 mb-3 text-sm"
            />
            <input
              value={suggestForm.suggested_by_name}
              onChange={(e) => setSuggestForm((f) => ({ ...f, suggested_by_name: e.target.value }))}
              placeholder="Your name (optional)"
              className="w-full border border-border rounded-lg p-2 mb-4 text-sm"
            />
            <div className="flex gap-2">
              <button onClick={() => setShowSuggestModal(false)} className="flex-1 border border-border py-2 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => suggestMut.mutate(suggestForm)}
                disabled={!suggestForm.label || suggestMut.isPending}
                className="flex-1 bg-primary text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Claim modal */}
      {showClaimModal && (
        <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50">
          <div className="bg-white w-full sm:max-w-md rounded-t-2xl sm:rounded-2xl p-6">
            <h3 className="font-bold text-lg mb-4">I can bring this</h3>
            <input
              value={claimForm.claimer_name}
              onChange={(e) => setClaimForm((f) => ({ ...f, claimer_name: e.target.value }))}
              placeholder="Your name (optional)"
              className="w-full border border-border rounded-lg p-2 mb-3 text-sm"
            />
            <input
              value={claimForm.claimer_phone}
              onChange={(e) => setClaimForm((f) => ({ ...f, claimer_phone: e.target.value }))}
              placeholder="WhatsApp number for coordination (optional)"
              className="w-full border border-border rounded-lg p-2 mb-4 text-sm"
            />
            <div className="flex gap-2">
              <button onClick={() => setShowClaimModal(null)} className="flex-1 border border-border py-2 rounded-lg text-sm">Cancel</button>
              <button
                onClick={() => claimMut.mutate({ resourceId: showClaimModal, form: claimForm })}
                disabled={claimMut.isPending}
                className="flex-1 bg-primary text-white py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
