import { useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getOrganisationsMap } from '../api'
import type { Organisation } from '../types'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const ORG_TYPES = ['ALL', 'HOSPITAL', 'AMBULANCE', 'PHARMACY', 'TOWING', 'FIRE_SAFETY', 'NGO', 'AGENCY', 'OTHER']

export default function OrgsPage() {
  const [typeFilter, setTypeFilter] = useState('ALL')
  const [zoneFilter, setZoneFilter] = useState('')

  const { data: orgs = [] } = useQuery<Organisation[]>({
    queryKey: ['orgs-map'],
    queryFn: getOrganisationsMap,
  })

  const filtered = orgs.filter((o) =>
    (typeFilter === 'ALL' || o.org_type === typeFilter) &&
    (!zoneFilter || o.zone_name.toLowerCase().includes(zoneFilter.toLowerCase()))
  )

  return (
    <div className="min-h-screen bg-bg font-sans">
      <div className="bg-white border-b border-border px-6 py-4 flex items-center gap-4">
        <Link to="/" className="font-bold text-primary text-lg">🚨 Siren.ng</Link>
        <span className="text-textBody">Verified Partners</span>
      </div>

      {/* Map */}
      <div style={{ height: 280 }}>
        <MapContainer center={[6.5244, 3.3792]} zoom={12} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap contributors" />
          {filtered.filter((o) => o.location_lat && o.location_lng).map((org) => (
            <Marker key={org.id} position={[org.location_lat, org.location_lng]}>
              <Popup>
                <strong>{org.name}</strong><br />
                {org.org_type} · {org.zone_name}<br />
                {org.operating_hours}
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-4">
        {/* Filters */}
        <div className="flex gap-2 mb-4 overflow-x-auto">
          {ORG_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap border transition ${typeFilter === t ? 'bg-primary text-white border-primary' : 'bg-white text-textBody border-border hover:border-primary'}`}
            >
              {t}
            </button>
          ))}
          <input
            value={zoneFilter}
            onChange={(e) => setZoneFilter(e.target.value)}
            placeholder="Zone..."
            className="border border-border rounded-full px-3 py-1 text-xs"
          />
        </div>

        {/* Org list */}
        <div className="space-y-3">
          {filtered.length === 0 && <p className="text-textMuted text-center py-6">No organisations found.</p>}
          {filtered.map((org) => (
            <div key={org.id} className="bg-white rounded-xl border border-border p-4">
              <div className="flex items-start justify-between">
                <div>
                  <span className="font-semibold text-textPrimary">{org.name}</span>
                  <span className="ml-2 bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full">✓ Verified</span>
                </div>
                <span className="text-xs text-textMuted">{org.zone_name}</span>
              </div>
              <div className="flex gap-3 mt-2 text-xs text-textMuted">
                <span>{org.org_type.replace('_', ' ')}</span>
                <span>·</span>
                <span>{org.operating_hours}</span>
                <span>·</span>
                <span>{org.total_responses} responses</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
