import { useState } from 'react'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { useMutation } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import Nav from '../components/Nav'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

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


export default function WatchPage() {
  return (
    <div className="min-h-screen bg-bg font-sans">
      <Nav />
      <div className="bg-white border-b border-border px-6 py-4">
        <h1 className="font-bold text-lg text-textPrimary">Watch Locations</h1>
        <p className="text-textMuted text-sm">Get instant alerts when emergencies happen near places you care about</p>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6 space-y-6">
        {/* Guardian Mode callout */}
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
          <span className="text-red-500 text-lg mt-0.5">&#9873;</span>
          <div>
            <p className="font-semibold text-red-900 text-sm">New: Guardian Mode (LGA-based)</p>
            <p className="text-red-700 text-xs mt-0.5">
              Subscribe to entire Lagos LGAs — no map pin needed. Works even when incident coordinates are missing.
            </p>
            <Link to="/guardian" className="inline-block mt-2 text-xs font-semibold text-red-700 underline">
              Set up Guardian Mode →
            </Link>
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

    </div>
  )
}
