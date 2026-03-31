import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Marker, Polyline, useMapEvents } from 'react-leaflet'
import Nav from '../components/Nav'
import L from 'leaflet'
import { useQuery } from '@tanstack/react-query'
import { getActiveIncidents, getOrganisationsMap, getSubscriptions, getHistoricalIncidents } from '../api'
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

const TYPE_ICON: Record<string, string> = {
  FIRE: '🔥', FLOOD: '🌊', COLLAPSE: '🏚', RTA: '🚗',
  EXPLOSION: '💥', DROWNING: '🆘', HAZARD: '⚡',
}

function severityColor(severity: string) {
  return severity === 'CRITICAL' || severity === 'HIGH' ? '#C0392B' : '#D35400'
}
function severityRadius(severity: string) {
  return severity === 'CRITICAL' ? 16 : severity === 'HIGH' ? 12 : 8
}

// Tracks zoom level inside the map context
function ZoomTracker({ onZoom }: { onZoom: (z: number) => void }) {
  useMapEvents({ zoomend(e) { onZoom(e.target.getZoom()) } })
  return null
}

interface ZoneCluster {
  zone_name: string
  lat: number
  lng: number
  count: number
  type: string
}

function buildZoneClusters(incidents: Incident[]): ZoneCluster[] {
  const map: Record<string, { lats: number[]; lngs: number[]; count: number; type: string }> = {}
  for (const inc of incidents) {
    if (!inc.location_lat || !inc.location_lng) continue
    const key = inc.zone_name || 'Lagos'
    if (!map[key]) map[key] = { lats: [], lngs: [], count: 0, type: inc.incident_type }
    map[key].lats.push(inc.location_lat)
    map[key].lngs.push(inc.location_lng)
    map[key].count++
  }
  return Object.entries(map).map(([zone_name, v]) => ({
    zone_name,
    lat: v.lats.reduce((a, b) => a + b, 0) / v.lats.length,
    lng: v.lngs.reduce((a, b) => a + b, 0) / v.lngs.length,
    count: v.count,
    type: v.type,
  }))
}

export default function MapPage() {
  const [typeFilter, setTypeFilter] = useState('ALL')
  const [showSaved, setShowSaved] = useState(true)
  const [showHistory, setShowHistory] = useState(false)
  const [zoom, setZoom] = useState(12)
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

  const { data: histData } = useQuery({
    queryKey: ['historical-map', typeFilter],
    queryFn: () => getHistoricalIncidents({
      page_size: '300',
      ...(typeFilter !== 'ALL' ? { incident_type: typeFilter } : {}),
    }),
    enabled: showHistory,
    staleTime: 5 * 60 * 1000,
  })
  const historicalIncidents: Incident[] = histData?.results || []

  useEffect(() => {
    if (data) setIncidents(data)
  }, [data, setIncidents])

  const filtered = typeFilter === 'ALL'
    ? incidents
    : incidents.filter((i) => i.incident_type === typeFilter)

  // At low zoom, collapse historical into zone-level cluster circles
  const histWithCoords = historicalIncidents.filter((i) => i.location_lat && i.location_lng)
  const zoneClusters = buildZoneClusters(histWithCoords)

  return (
    <div className="h-screen flex flex-col font-sans">
      <Nav />
      {/* Filter bar */}
      <div className="bg-white border-b border-border px-4 py-2 flex gap-2 overflow-x-auto z-10">
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
      <div className="flex-1 relative">
        <MapContainer
          center={[6.5244, 3.3792]}
          zoom={12}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="© OpenStreetMap contributors"
          />
          <ZoomTracker onZoom={setZoom} />

          {/* Live incidents */}
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

          {/* Historical layer */}
          {showHistory && zoom >= 11 && histWithCoords.map((inc) => (
            <CircleMarker
              key={`h-${inc.id}`}
              center={[inc.location_lat!, inc.location_lng!]}
              radius={5}
              color="#9CA3AF"
              fillColor="#9CA3AF"
              fillOpacity={0.5}
              weight={1}
            >
              <Popup>
                <div className="text-xs leading-relaxed">
                  <div className="flex items-center gap-1 mb-1">
                    <span>{TYPE_ICON[inc.incident_type] || '🚨'}</span>
                    <strong>{inc.incident_type}</strong>
                  </div>
                  <div className="text-gray-500">{inc.zone_name} · {new Date(inc.created_at).toLocaleDateString('en-NG', { month: 'short', year: 'numeric' })}</div>
                  <div className="text-gray-400 mt-0.5">{inc.severity}</div>
                  <div className="text-green-700 font-medium mt-0.5">✓ Resolved</div>
                  <a href={`/track/${inc.id}`} className="text-blue-600 hover:underline block mt-1">View zone history →</a>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          {/* Historical zone clusters at low zoom */}
          {showHistory && zoom < 11 && zoneClusters.map((cluster) => (
            <CircleMarker
              key={`cluster-${cluster.zone_name}`}
              center={[cluster.lat, cluster.lng]}
              radius={Math.min(5 + Math.sqrt(cluster.count) * 2, 20)}
              color="#9CA3AF"
              fillColor="#9CA3AF"
              fillOpacity={0.4}
              weight={1}
            >
              <Popup>
                <div className="text-xs">
                  <strong>{cluster.zone_name}</strong>
                  <br />
                  {cluster.count} historical incident{cluster.count !== 1 ? 's' : ''}
                  <br />
                  <span className="text-green-700">All resolved</span>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          {/* Orgs */}
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

          {/* Saved locations */}
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

        {/* History toggle — bottom right, above zoom controls */}
        <div className="absolute bottom-24 right-3 z-[1000]">
          <button
            onClick={() => setShowHistory((v) => !v)}
            className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-semibold shadow-md border transition-all ${
              showHistory
                ? 'bg-[#0D9488] text-white border-[#0D9488]'
                : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
            }`}
          >
            <span
              className="w-3 h-3 rounded-full inline-block"
              style={{ background: showHistory ? 'rgba(255,255,255,0.6)' : '#9CA3AF' }}
            />
            {showHistory ? 'History: ON' : 'Show history (2010–2025)'}
          </button>
        </div>
      </div>
    </div>
  )
}
