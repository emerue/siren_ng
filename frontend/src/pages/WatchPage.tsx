import { useState } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { createSubscription, getSubscriptions, updateSubscription, deleteSubscription, getZoneHistory } from '../api'
import type { LocationSubscription, ZoneHistory } from '../types'
import { createHash } from '../utils/hash'
import Nav from '../components/Nav'
import ZoneSafetyScoreCard from '../components/ZoneSafetyScoreCard'
import ZoneHistoryPanel from '../components/ZoneHistoryPanel'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

// Extract Lagos zone name from a free-text label
const KNOWN_ZONES = [
  'Ikeja', 'Surulere', 'Lekki', 'Victoria Island', 'Ajah', 'Ikorodu', 'Badagry',
  'Alimosho', 'Oshodi', 'Mushin', 'Agege', 'Kosofe', 'Apapa', 'Lagos Island',
  'Yaba', 'Orile', 'Ojo', 'Ajegunle', 'Isale Eko', 'Festac', 'Ipaja', 'Egbeda',
  'Ojodu', 'Berger', 'Gbagada', 'Maryland', 'Ketu', 'Mile 12', 'Iyana-Ipaja',
  'Sangotedo', 'Epe', 'Ibeju-Lekki', 'Magodo', 'Ojota', 'Ogudu', 'Anthony',
  'Palmgrove', 'Bariga', 'Shomolu', 'Abule-Egba', 'Dopemu', 'Ijora', 'Ejigbo',
]

function guessZone(label: string): string {
  const lower = label.toLowerCase()
  for (const z of KNOWN_ZONES) {
    if (lower.includes(z.toLowerCase())) return z
  }
  return 'Lagos'
}

function PinPicker({ onSelect }: { onSelect: (lat: number, lng: number) => void }) {
  useMapEvents({ click(e) { onSelect(e.latlng.lat, e.latlng.lng) } })
  return null
}

function CommuteForm() {
  const [form, setForm] = useState({
    whatsapp_number: '', label: 'My commute',
    home_lat: null as number | null, home_lng: null as number | null,
    office_lat: null as number | null, office_lng: null as number | null,
    commute_buffer_km: 1.5,
  })
  const [pinMode, setPinMode] = useState<'home' | 'office'>('home')

  const mut = useMutation({
    mutationFn: () => import('../api').then(({ createCommuteSubscription }) =>
      createCommuteSubscription({
        whatsapp_number: form.whatsapp_number, label: form.label,
        location_lat: form.home_lat, location_lng: form.home_lng,
        office_lat: form.office_lat, office_lng: form.office_lng,
        commute_buffer_km: form.commute_buffer_km,
      })
    ),
    onSuccess: () => { alert('Commute Shield active! You will receive peak-hour route alerts.') },
  })

  return (
    <div className="space-y-3">
      <input
        value={form.whatsapp_number}
        onChange={(e) => setForm((f) => ({ ...f, whatsapp_number: e.target.value }))}
        placeholder="WhatsApp number (+2348012345678)"
        className="w-full border border-border rounded-lg p-3 text-sm"
      />
      <div className="flex gap-2">
        {(['home', 'office'] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setPinMode(mode)}
            className={`flex-1 py-2 rounded-lg text-xs font-semibold border ${pinMode === mode ? 'bg-primary text-white border-primary' : 'border-border'}`}
          >
            Set {mode.charAt(0).toUpperCase() + mode.slice(1)} {form[`${mode}_lat`] ? '(set)' : ''}
          </button>
        ))}
      </div>
      <p className="text-textMuted text-xs">Tap the map to set your {pinMode} location</p>
      <div className="rounded-xl overflow-hidden border border-border" style={{ height: 200 }}>
        <MapContainer center={[6.5244, 3.3792]} zoom={12} style={{ height: '100%', width: '100%' }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <PinPicker onSelect={(lat, lng) => {
            if (pinMode === 'home') setForm((f) => ({ ...f, home_lat: lat, home_lng: lng }))
            else setForm((f) => ({ ...f, office_lat: lat, office_lng: lng }))
          }} />
          {form.home_lat && form.home_lng && <Marker position={[form.home_lat, form.home_lng]} />}
          {form.office_lat && form.office_lng && <Marker position={[form.office_lat, form.office_lng]} />}
        </MapContainer>
      </div>
      {mut.isError && <p className="text-primary text-sm">Failed. Please check details.</p>}
      {mut.isSuccess && <p className="text-success text-sm">Commute Shield active!</p>}
      <button
        onClick={() => mut.mutate()}
        disabled={!form.whatsapp_number || !form.home_lat || !form.office_lat || mut.isPending}
        className="w-full bg-primary text-white py-3 rounded-lg font-semibold text-sm disabled:opacity-50"
      >
        {mut.isPending ? 'Saving...' : 'Activate Commute Shield'}
      </button>
    </div>
  )
}

// Mini wrapper: fetches zone history to get total + trend for each sub
function SubScoreCard({ sub, onOpenHistory }: { sub: LocationSubscription; onOpenHistory: (zone: string, label: string) => void }) {
  const zone = guessZone(sub.label)
  const { data } = useQuery<ZoneHistory>({
    queryKey: ['zone-history', zone],
    queryFn: () => getZoneHistory(zone),
    staleTime: 10 * 60 * 1000,
  })

  return (
    <ZoneSafetyScoreCard
      sub={sub}
      zoneName={zone}
      totalIncidents={data?.total_incidents}
      trend={data?.trend}
      onOpenHistory={() => onOpenHistory(zone, sub.label)}
    />
  )
}

export default function WatchPage() {
  const qc = useQueryClient()
  const [managePhone, setManagePhone] = useState('')
  const [manageHash, setManageHash] = useState('')
  const [historyPanel, setHistoryPanel] = useState<{ zone: string; label: string } | null>(null)
  const [form, setForm] = useState({
    whatsapp_number: '', label: '', location_type: 'HOME',
    location_lat: null as number | null, location_lng: null as number | null,
    alert_radius_km: 1.0, incident_types: [] as string[],
  })

  const createMut = useMutation({
    mutationFn: () => createSubscription(form),
    onSuccess: () => {
      alert('Location saved! You will receive WhatsApp alerts for incidents in your chosen radius.')
      setForm({ whatsapp_number: '', label: '', location_type: 'HOME', location_lat: null, location_lng: null, alert_radius_km: 1.0, incident_types: [] })
    },
  })

  const { data: subs = [], isLoading: loadingSubs } = useQuery<LocationSubscription[]>({
    queryKey: ['subscriptions', manageHash],
    queryFn: () => getSubscriptions(manageHash),
    enabled: !!manageHash,
  })

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteSubscription(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions', manageHash] }),
  })

  const pauseMut = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateSubscription(id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['subscriptions', manageHash] }),
  })

  async function handleLookup() {
    const hash = await createHash(managePhone)
    setManageHash(hash)
  }

  return (
    <div className="min-h-screen bg-bg font-sans">
      <Nav />
      <div className="bg-white border-b border-border px-6 py-4">
        <h1 className="font-bold text-lg text-textPrimary">Watch Locations</h1>
        <p className="text-textMuted text-sm">Get instant alerts when emergencies happen near places you care about</p>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6 space-y-6">
        {/* Save a location form */}
        <div className="bg-white rounded-xl border border-border p-5">
          <h3 className="font-bold mb-4">Save a location to watch</h3>
          <input
            value={form.whatsapp_number}
            onChange={(e) => setForm((f) => ({ ...f, whatsapp_number: e.target.value }))}
            placeholder="WhatsApp number for alerts (e.g. +2348012345678)"
            className="w-full border border-border rounded-lg p-3 text-sm mb-3"
          />
          <input
            value={form.label}
            onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
            placeholder="Location name (e.g. My house, Timi school Surulere)"
            className="w-full border border-border rounded-lg p-3 text-sm mb-3"
          />
          <select
            value={form.location_type}
            onChange={(e) => setForm((f) => ({ ...f, location_type: e.target.value }))}
            className="w-full border border-border rounded-lg p-3 text-sm mb-3"
          >
            {[['HOME','Home'],['SCHOOL','School/Child location'],['LAND','Land/Property'],['OFFICE','Office'],['FAMILY','Family member location'],['OTHER','Other']].map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>

          <p className="text-textMuted text-xs mb-2">Tap the map to pin the location</p>
          <div className="rounded-xl overflow-hidden border border-border mb-3" style={{ height: 200 }}>
            <MapContainer center={[6.5244, 3.3792]} zoom={12} style={{ height: '100%', width: '100%' }}>
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <PinPicker onSelect={(lat, lng) => setForm((f) => ({ ...f, location_lat: lat, location_lng: lng }))} />
              {form.location_lat && form.location_lng && (
                <Marker position={[form.location_lat, form.location_lng]} />
              )}
            </MapContainer>
          </div>
          <button
            onClick={() => navigator.geolocation.getCurrentPosition((pos) =>
              setForm((f) => ({ ...f, location_lat: pos.coords.latitude, location_lng: pos.coords.longitude }))
            )}
            className="text-primary text-sm mb-3 hover:underline"
          >
            Use my current location
          </button>

          <div className="grid grid-cols-4 gap-2 mb-4">
            {[[0.5,'500m'],[1.0,'1km'],[2.0,'2km'],[5.0,'5km']].map(([val, label]) => (
              <button
                key={val}
                onClick={() => setForm((f) => ({ ...f, alert_radius_km: val as number }))}
                className={`py-2 rounded-lg text-xs font-semibold border transition ${form.alert_radius_km === val ? 'bg-primary text-white border-primary' : 'bg-white text-textBody border-border hover:border-primary'}`}
              >
                {label}
              </button>
            ))}
          </div>

          {createMut.isError && <p className="text-primary text-sm mb-2">Failed. Please check your details.</p>}
          {createMut.isSuccess && <p className="text-success text-sm mb-2">Location saved!</p>}
          <button
            onClick={() => createMut.mutate()}
            disabled={!form.whatsapp_number || !form.label || !form.location_lat || createMut.isPending}
            className="w-full bg-primary text-white py-3 rounded-lg font-semibold text-sm disabled:opacity-50"
          >
            {createMut.isPending ? 'Saving...' : 'Save Location'}
          </button>
        </div>

        {/* Manage saved locations */}
        <div className="bg-white rounded-xl border border-border p-5">
          <h3 className="font-bold mb-3">Manage saved locations</h3>
          <div className="flex gap-2 mb-4">
            <input
              value={managePhone}
              onChange={(e) => setManagePhone(e.target.value)}
              placeholder="+2348012345678"
              className="flex-1 border border-border rounded-lg p-2 text-sm"
            />
            <button
              onClick={handleLookup}
              className="bg-primary text-white px-4 py-2 rounded-lg text-sm font-semibold"
            >
              Look up
            </button>
          </div>

          {loadingSubs && <p className="text-textMuted text-sm">Loading...</p>}
          {manageHash && !loadingSubs && subs.length === 0 && (
            <p className="text-textMuted text-sm">No saved locations found for this number.</p>
          )}

          {/* Safety score cards (STATE 2 — INVESTED) */}
          {subs.length > 0 && (
            <div className="grid grid-cols-2 gap-3 mb-4">
              {subs.map((sub) => (
                <SubScoreCard
                  key={sub.id}
                  sub={sub}
                  onOpenHistory={(zone, label) => setHistoryPanel({ zone, label })}
                />
              ))}
            </div>
          )}

          {/* Compact controls below cards */}
          <div className="space-y-2">
            {subs.map((sub) => (
              <div key={sub.id} className="flex items-center justify-between border border-border rounded-lg p-3">
                <div>
                  <div className="font-medium text-textPrimary text-sm">{sub.label}</div>
                  <div className="text-textMuted text-xs">{sub.location_type} · {sub.alert_radius_km}km · {sub.is_active ? 'Active' : 'Paused'}</div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => pauseMut.mutate({ id: sub.id, is_active: !sub.is_active })}
                    className="text-xs border border-border px-2 py-1 rounded hover:border-primary"
                  >
                    {sub.is_active ? 'Pause' : 'Resume'}
                  </button>
                  <button
                    onClick={() => deleteMut.mutate(sub.id)}
                    className="text-xs text-red-600 border border-red-200 px-2 py-1 rounded hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Commute Shield */}
        <div className="bg-white rounded-xl border border-border p-5">
          <h3 className="font-bold mb-1">Commute Shield</h3>
          <p className="text-textBody text-sm mb-3">
            Get alerts when incidents block your daily route. Monitors your Home to Office corridor
            during peak hours (6–10am and 4–8pm).
          </p>
          <CommuteForm />
        </div>

        <p className="text-textMuted text-xs text-center pb-4">
          Prefer WhatsApp? You can also manage locations via Siren on WhatsApp.{' '}
          <Link to="/connect" className="text-green-700 hover:underline">Connect WhatsApp →</Link>
        </p>
      </div>

      {/* Zone History Drawer */}
      {historyPanel && (
        <ZoneHistoryPanel
          zoneName={historyPanel.zone}
          locationLabel={historyPanel.label}
          isOpen={true}
          onClose={() => setHistoryPanel(null)}
        />
      )}
    </div>
  )
}
