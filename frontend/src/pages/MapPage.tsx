import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Marker, Polyline } from 'react-leaflet'
import { Link } from 'react-router-dom'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { getActiveIncidents, getOrganisationsMap, getSubscriptions } from '../api'
import { useWebSocket } from '../hooks/useWebSocket'
import { useIncidentStore } from '../store/incidentStore'
import type { Incident, Organisation, LocationSubscription } from '../types'

// Fix default marker icons in webpack/vite
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const INCIDENT_TYPES = ['ALL', 'FIRE', 'FLOOD', 'COLLAPSE', 'RTA', 'EXPLOSION', 'DROWNING', 'HAZARD']

function severityColor(severity: string) {
  return severity === 'CRITICAL' || severity === 'HIGH' ? '#C0392B' : '#D35400'
}
function severityRadius(severity: string) {
  return severity === 'CRITICAL' ? 16 : severity === 'HIGH' ? 12 : 8
}

export default function MapPage() {
  const [typeFilter, setTypeFilter] = useState('ALL')
  const [showSaved, setShowSaved] = useState(true)
  const [phoneHash] = useState<string | null>(localStorage.getItem('siren_phone_hash'))
  const { setIncidents, incidents } = useIncidentStore()

  useWebSocket()

  const { data } = useQuery<Incident[]>({
    queryKey: ['active-incidents'],
    queryFn: getActiveIncidents,
    refetchInterval: 30_000,
  })

  const { data: orgs = [] } = useQuery<Organisation[]>({
    queryKey: ['orgs-map'],
    queryFn: getOrganisationsMap,
  })

  const { data: subs = [] } = useQuery<LocationSubscription[]>({
    queryKey: ['subscriptions-map', phoneHash],
    queryFn: () => getSubscriptions(phoneHash!),
    enabled: !!phoneHash,
  })

  useEffect(() => {
    if (data) setIncidents(data)
  }, [data, setIncidents])

  const filtered = typeFilter === 'ALL'
    ? incidents
    : incidents.filter((i) => i.incident_type === typeFilter)

  return (
    <div className="h-screen flex flex-col font-sans">
      {/* Filter bar */}
      <div className="bg-white border-b border-border px-4 py-2 flex gap-2 overflow-x-auto z-10">
        <Link to="/" className="text-primary font-bold mr-2 whitespace-nowrap">🚨 Siren</Link>
        {INCIDENT_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap border transition ${
              typeFilter === t
                ? 'bg-primary text-white border-primary'
                : 'bg-white text-textBody border-border hover:border-primary'
            }`}
          >
            {t}
          </button>
        ))}
        {phoneHash && (
          <button
            onClick={() => setShowSaved(!showSaved)}
            className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap border transition ${
              showSaved
                ? 'bg-green-600 text-white border-green-600'
                : 'bg-white text-textBody border-border hover:border-green-600'
            }`}
          >
            {showSaved ? '❤️ My Locations: ON' : '🤍 My Locations: OFF'}
          </button>
        )}
      </div>

      {/* Map */}
      <div className="flex-1">
        <MapContainer
          center={[6.5244, 3.3792]}
          zoom={12}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="© OpenStreetMap contributors"
          />

          {filtered.filter((i) => i.location_lat && i.location_lng).map((inc) => (
            <CircleMarker
              key={inc.id}
              center={[inc.location_lat!, inc.location_lng!]}
              radius={severityRadius(inc.severity)}
              color={severityColor(inc.severity)}
              fillColor={severityColor(inc.severity)}
              fillOpacity={0.7}
            >
              <Popup>
                <div className="text-sm">
                  <strong>{inc.incident_type}</strong>
                  <br />
                  {inc.severity} — {inc.status}
                  <br />
                  {inc.zone_name}
                  <br />
                  {inc.vouch_count > 0 && <span>👍 {inc.vouch_count} vouches · </span>}
                  {inc.donation_count > 0 && <span>₦{inc.total_donations_naira?.toLocaleString()} raised</span>}
                  <br />
                  <a href={`/track/${inc.id}`} className="text-primary font-semibold">View full details →</a>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          {orgs.filter((o) => o.location_lat && o.location_lng).map((org) => (
            <Marker key={org.id} position={[org.location_lat, org.location_lng]}>
              <Popup>
                <div className="text-sm">
                  <strong>{org.name}</strong>
                  <br />
                  {org.org_type} · {org.zone_name}
                  <br />
                  {org.operating_hours}
                </div>
              </Popup>
            </Marker>
          ))}

          {showSaved && subs.map((sub) => (
            <div key={sub.id}>
              <Marker
                position={[sub.location_lat, sub.location_lng]}
                icon={L.divIcon({
                  className: 'bg-transparent',
                  html: '<div class="text-2xl">❤️</div>',
                  iconSize: [30, 30],
                  iconAnchor: [15, 15]
                })}
              >
                <Popup>{sub.label}</Popup>
              </Marker>
              {sub.subscription_type === 'COMMUTE' && sub.office_lat && sub.office_lng && (
                <>
                  <Marker
                    position={[sub.office_lat, sub.office_lng]}
                    icon={L.divIcon({
                      className: 'bg-transparent',
                      html: '<div class="text-2xl">🏢</div>',
                      iconSize: [30, 30],
                      iconAnchor: [15, 15]
                    })}
                  >
                    <Popup>{sub.label} Office</Popup>
                  </Marker>
                  <Polyline
                    positions={[
                      [sub.location_lat, sub.location_lng],
                      [sub.office_lat, sub.office_lng]
                    ]}
                    color="#C0392B"
                    weight={4}
                    dashArray="10, 10"
                    opacity={0.6}
                  >
                    <Popup>{sub.label} Commute Route</Popup>
                  </Polyline>
                </>
              )}
            </div>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
