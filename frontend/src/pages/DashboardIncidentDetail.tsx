import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker } from 'react-leaflet'
import L from 'leaflet'
import { formatDistanceToNow } from 'date-fns'
import { getIncident, getResources, getDonationSummary, dispatchIncident, resolveIncident, deleteMedia } from '../api'
import DashboardLayout from '../components/DashboardLayout'
import type { Incident, ResourceItem, IncidentMedia } from '../types'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

function AdminMediaGallery({ incidentId, media }: { incidentId: string; media: IncidentMedia[] }) {
  const qc = useQueryClient()
  const [lightbox, setLightbox] = useState<IncidentMedia | null>(null)
  const [confirm, setConfirm] = useState<number | null>(null)

  const deleteMut = useMutation({
    mutationFn: (mediaId: number) => deleteMedia(incidentId, mediaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['incident', incidentId] })
      setConfirm(null)
    },
  })

  if (media.length === 0) return null

  return (
    <div className="bg-white rounded-xl border border-border p-5 mb-4">
      <h3 className="font-semibold text-textPrimary mb-3">
        Media Evidence · {media.length} file{media.length !== 1 ? 's' : ''}
      </h3>
      <div className="grid grid-cols-3 gap-2">
        {media.map((m) => (
          <div key={m.id} className="relative group">
            <button
              onClick={() => m.media_type === 'image' && setLightbox(m)}
              className="w-full aspect-square rounded-lg overflow-hidden bg-gray-100 block"
            >
              {m.media_type === 'image' ? (
                <img src={m.public_url} alt="" className="w-full h-full object-cover group-hover:opacity-90 transition" />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center bg-gray-900 text-white">
                  <span className="text-3xl">▶</span>
                  <span className="text-xs opacity-70 mt-1">Video</span>
                </div>
              )}
            </button>
            {/* Delete button */}
            <button
              onClick={() => setConfirm(m.id)}
              className="absolute top-1 right-1 w-6 h-6 bg-red-600 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition flex items-center justify-center shadow"
            >
              ×
            </button>
            <p className="text-xs text-textMuted mt-1 text-center">
              {(m.file_size / 1024).toFixed(0)}KB
            </p>
          </div>
        ))}
      </div>

      {/* Delete confirm */}
      {confirm !== null && (
        <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 flex items-center justify-between">
          <span className="text-sm text-red-700">Delete this file permanently?</span>
          <div className="flex gap-2">
            <button onClick={() => setConfirm(null)} className="text-xs px-3 py-1 border border-border rounded-lg">Cancel</button>
            <button
              onClick={() => deleteMut.mutate(confirm)}
              disabled={deleteMut.isPending}
              className="text-xs px-3 py-1 bg-red-600 text-white rounded-lg disabled:opacity-50"
            >
              {deleteMut.isPending ? '...' : 'Delete'}
            </button>
          </div>
        </div>
      )}

      {/* Lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center p-4"
          onClick={() => setLightbox(null)}
        >
          <button className="absolute top-4 right-4 text-white text-3xl w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded-full">×</button>
          <img src={lightbox.public_url} alt="" className="max-w-full max-h-full rounded-lg shadow-2xl" onClick={e => e.stopPropagation()} />
        </div>
      )}
    </div>
  )
}

export default function DashboardIncidentDetail() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()

  const { data: incident, isLoading } = useQuery<Incident>({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id!),
    enabled: !!id,
  })

  const { data: resources = [] } = useQuery<ResourceItem[]>({
    queryKey: ['resources', id],
    queryFn: () => getResources(id!),
    enabled: !!id,
  })

  const { data: donationSummary } = useQuery({
    queryKey: ['donation-summary', id],
    queryFn: () => getDonationSummary(id!),
    enabled: !!id,
  })

  const dispatchMut = useMutation({
    mutationFn: () => dispatchIncident(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incident', id] }),
  })
  const resolveMut = useMutation({
    mutationFn: () => resolveIncident(id!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incident', id] }),
  })

  if (isLoading) return <DashboardLayout><div className="p-8 text-textMuted">Loading...</div></DashboardLayout>
  if (!incident) return <DashboardLayout><div className="p-8 text-textMuted">Not found.</div></DashboardLayout>

  const mediaItems: IncidentMedia[] = incident.media ?? []

  return (
    <DashboardLayout>
      <div className="p-8 max-w-3xl">
        <div className="flex items-center gap-2 mb-6">
          <Link to="/dashboard" className="text-textMuted text-sm hover:text-primary">Dashboard</Link>
          <span className="text-textMuted">/</span>
          <span className="text-textPrimary text-sm font-medium">{incident.incident_type} — {incident.zone_name}</span>
        </div>

        {/* Status + actions */}
        <div className="bg-white rounded-xl border border-border p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <span className="font-bold text-xl text-textPrimary">{incident.incident_type}</span>
              <span className="ml-2 text-textMuted">{incident.severity} · {incident.status}</span>
            </div>
            <div className="flex gap-2">
              <button onClick={() => dispatchMut.mutate()} className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700">Dispatch</button>
              <button onClick={() => resolveMut.mutate()} className="bg-success text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-green-800">Resolve</button>
            </div>
          </div>
          <p className="text-textBody text-sm mb-3">{incident.description}</p>
          <div className="text-xs text-textMuted">
            {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })} ·
            {incident.vouch_count} vouches ·
            AI confidence: {(incident.ai_confidence * 100).toFixed(0)}% ·
            Fraud score: {(incident.fraud_score * 100).toFixed(0)}%
          </div>
        </div>

        {/* Media */}
        {mediaItems.length > 0 && (
          <AdminMediaGallery incidentId={id!} media={mediaItems} />
        )}

        {/* AI result */}
        {incident.ai_raw_response && Object.keys(incident.ai_raw_response).length > 0 && (
          <div className="bg-white rounded-xl border border-border p-5 mb-4">
            <h3 className="font-semibold mb-2 text-textPrimary">AI Verification Result</h3>
            <pre className="text-xs text-textBody overflow-x-auto bg-gray-50 p-3 rounded-lg">
              {JSON.stringify(incident.ai_raw_response, null, 2)}
            </pre>
          </div>
        )}

        {/* Map */}
        {incident.location_lat && incident.location_lng && (
          <div className="rounded-xl overflow-hidden border border-border mb-4" style={{ height: 250 }}>
            <MapContainer center={[incident.location_lat, incident.location_lng]} zoom={15} style={{ height: '100%', width: '100%' }}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Marker position={[incident.location_lat, incident.location_lng]} />
            </MapContainer>
          </div>
        )}

        {/* Timeline */}
        {(incident.response_logs || []).length > 0 && (
          <div className="bg-white rounded-xl border border-border p-5 mb-4">
            <h3 className="font-semibold mb-3 text-textPrimary">Timeline</h3>
            <div className="space-y-2">
              {incident.response_logs!.map((log) => (
                <div key={log.id} className="flex gap-3 text-sm">
                  <div className="w-2 h-2 rounded-full bg-primary mt-1.5 shrink-0"></div>
                  <div>
                    <span className="font-medium">{log.to_status}</span>
                    {log.note && <span className="text-textMuted"> — {log.note}</span>}
                    <div className="text-xs text-textMuted">{log.actor} · {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Resources */}
        {resources.length > 0 && (
          <div className="bg-white rounded-xl border border-border p-5 mb-4">
            <h3 className="font-semibold mb-3 text-textPrimary">Resources ({resources.length})</h3>
            <div className="space-y-2">
              {resources.map((r) => (
                <div key={r.id} className="flex items-center justify-between text-sm border-b border-border pb-2">
                  <span className={r.status === 'ARRIVED' ? 'line-through text-textMuted' : 'text-textPrimary'}>{r.label}</span>
                  <span className="text-xs text-textMuted">{r.status} · {r.claim_count} claims</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Donations */}
        {donationSummary && (
          <div className="bg-white rounded-xl border border-border p-5">
            <h3 className="font-semibold mb-3 text-textPrimary">Donations</h3>
            <div className="text-2xl font-bold text-textPrimary">&#8358;{donationSummary.total_naira?.toLocaleString()}</div>
            <div className="text-textMuted text-sm">{donationSummary.donation_count} donors</div>
            {donationSummary.fund_breakdown && Object.entries(donationSummary.fund_breakdown).map(([fund, naira]) => (
              <div key={fund} className="flex justify-between text-sm mt-2">
                <span className="text-textBody">{fund}</span>
                <span className="font-medium">&#8358;{(naira as number).toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}
