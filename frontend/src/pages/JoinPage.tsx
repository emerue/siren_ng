import { useState } from 'react'
import Nav from '../components/Nav'
import { useMutation } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { registerResponder, registerOrganisation } from '../api'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const WHATSAPP_NUMBER = import.meta.env.VITE_WHATSAPP_NUMBER || '+2349000000000'
const WA = WHATSAPP_NUMBER.replace('+', '')

const SKILL_CATEGORIES = [
  'MEDICAL_ADVANCED',
  'MEDICAL_BASIC',
  'FIRE',
  'FLOOD_RESCUE',
  'STRUCTURAL',
  'ELECTRICAL',
  'FIRST_AID',
]
const SKILL_LABELS: Record<string, string> = {
  MEDICAL_ADVANCED: 'Medical — Advanced (Doctor/Surgeon)',
  MEDICAL_BASIC: 'Medical — Basic (Nurse/Paramedic)',
  FIRE: 'Fire Response',
  FLOOD_RESCUE: 'Water / Flood Rescue',
  STRUCTURAL: 'Structural Rescue',
  ELECTRICAL: 'Electrical',
  FIRST_AID: 'First Aid / CPR',
}

const ORG_TYPES = ['HOSPITAL', 'AMBULANCE', 'PHARMACY', 'TOWING', 'FIRE_SAFETY', 'NGO', 'GOVERNMENT']
const ORG_LABELS: Record<string, string> = {
  HOSPITAL: 'Hospital / Clinic',
  AMBULANCE: 'Ambulance Service',
  PHARMACY: 'Pharmacy',
  TOWING: 'Towing / Heavy Equipment',
  FIRE_SAFETY: 'Fire Safety',
  NGO: 'NGO / Community Group',
  GOVERNMENT: 'Government Agency',
}

const INCIDENT_TYPES = ['FIRE', 'FLOOD', 'COLLAPSE', 'RTA', 'EXPLOSION', 'DROWNING', 'HAZARD']

function PinPicker({ onSelect }: { onSelect: (lat: number, lng: number) => void }) {
  useMapEvents({ click(e) { onSelect(e.latlng.lat, e.latlng.lng) } })
  return null
}

function ChannelToggle({
  channel,
  onChange,
}: {
  channel: 'whatsapp' | 'web'
  onChange: (c: 'whatsapp' | 'web') => void
}) {
  return (
    <div className="flex rounded-xl border border-border overflow-hidden mb-6">
      <button
        onClick={() => onChange('whatsapp')}
        className={`flex-1 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition ${
          channel === 'whatsapp' ? 'bg-green-600 text-white' : 'bg-white text-textBody hover:bg-green-50'
        }`}
      >
        📱 Via WhatsApp
      </button>
      <button
        onClick={() => onChange('web')}
        className={`flex-1 py-3 text-sm font-semibold flex items-center justify-center gap-2 transition ${
          channel === 'web' ? 'bg-primary text-white' : 'bg-white text-textBody hover:bg-red-50'
        }`}
      >
        💻 Via Web Form
      </button>
    </div>
  )
}

function ResponderWebForm() {
  const [form, setForm] = useState({
    name: '',
    whatsapp_number: '',
    skill_category: '',
    home_lat: null as number | null,
    home_lng: null as number | null,
    response_radius_km: 5,
    responds_to: [] as string[],
  })

  const mut = useMutation({
    mutationFn: () => registerResponder(form as Record<string, unknown>),
  })

  function toggleIncidentType(type: string) {
    setForm((f) => ({
      ...f,
      responds_to: f.responds_to.includes(type)
        ? f.responds_to.filter((t) => t !== type)
        : [...f.responds_to, type],
    }))
  }

  if (mut.isSuccess) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
        <div className="text-4xl mb-3">✅</div>
        <h3 className="font-bold text-textPrimary mb-2">Application submitted!</h3>
        <p className="text-textBody text-sm">
          Our team will verify your credentials and send you a WhatsApp confirmation. You'll start receiving alerts once verified.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">Full name</label>
        <input
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="e.g. Dr. Amaka Osei"
          className="w-full border border-border rounded-lg p-3 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">WhatsApp number (for alerts)</label>
        <input
          value={form.whatsapp_number}
          onChange={(e) => setForm((f) => ({ ...f, whatsapp_number: e.target.value }))}
          placeholder="+2348012345678"
          className="w-full border border-border rounded-lg p-3 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">Primary skill</label>
        <select
          value={form.skill_category}
          onChange={(e) => setForm((f) => ({ ...f, skill_category: e.target.value }))}
          className="w-full border border-border rounded-lg p-3 text-sm"
        >
          <option value="">Select skill category</option>
          {SKILL_CATEGORIES.map((s) => (
            <option key={s} value={s}>{SKILL_LABELS[s]}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-2">
          Incident types you can respond to
        </label>
        <div className="flex flex-wrap gap-2">
          {INCIDENT_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => toggleIncidentType(t)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                form.responds_to.includes(t)
                  ? 'bg-primary text-white border-primary'
                  : 'bg-white text-textBody border-border hover:border-primary'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-2">
          Response radius:{' '}
          <span className="text-primary font-bold">{form.response_radius_km} km</span>
        </label>
        <div className="grid grid-cols-4 gap-2">
          {[2, 5, 10, 20].map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setForm((f) => ({ ...f, response_radius_km: r }))}
              className={`py-2 rounded-lg text-xs font-semibold border transition ${
                form.response_radius_km === r
                  ? 'bg-primary text-white border-primary'
                  : 'bg-white text-textBody border-border hover:border-primary'
              }`}
            >
              {r} km
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">
          Home area — tap map to pin
        </label>
        <div className="rounded-xl overflow-hidden border border-border mb-2" style={{ height: 180 }}>
          <MapContainer center={[6.5244, 3.3792]} zoom={12} style={{ height: '100%', width: '100%' }}>
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <PinPicker onSelect={(lat, lng) => setForm((f) => ({ ...f, home_lat: lat, home_lng: lng }))} />
            {form.home_lat && form.home_lng && (
              <Marker position={[form.home_lat, form.home_lng]} />
            )}
          </MapContainer>
        </div>
        <button
          type="button"
          onClick={() =>
            navigator.geolocation.getCurrentPosition((pos) =>
              setForm((f) => ({ ...f, home_lat: pos.coords.latitude, home_lng: pos.coords.longitude }))
            )
          }
          className="text-primary text-xs hover:underline"
        >
          📍 Use my current location
        </button>
      </div>

      {mut.isError && (
        <p className="text-primary text-sm">Submission failed. Please check your details and try again.</p>
      )}

      <button
        onClick={() => mut.mutate()}
        disabled={
          mut.isPending ||
          !form.name ||
          !form.whatsapp_number ||
          !form.skill_category ||
          !form.home_lat
        }
        className="w-full bg-primary text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 hover:bg-red-700 transition"
      >
        {mut.isPending ? 'Submitting...' : 'Submit Application'}
      </button>
    </div>
  )
}

function OrgWebForm() {
  const [form, setForm] = useState({
    name: '',
    org_type: '',
    contact_name: '',
    contact_whatsapp: '',
    contact_phone: '',
    address: '',
    location_lat: null as number | null,
    location_lng: null as number | null,
    response_radius_km: 10,
    responds_to: [] as string[],
    operating_hours: '',
  })

  const mut = useMutation({
    mutationFn: () => registerOrganisation(form as Record<string, unknown>),
  })

  function toggleIncidentType(type: string) {
    setForm((f) => ({
      ...f,
      responds_to: f.responds_to.includes(type)
        ? f.responds_to.filter((t) => t !== type)
        : [...f.responds_to, type],
    }))
  }

  if (mut.isSuccess) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
        <div className="text-4xl mb-3">✅</div>
        <h3 className="font-bold text-textPrimary mb-2">Organisation registered!</h3>
        <p className="text-textBody text-sm">
          Our team will verify your organisation and activate your account. You'll receive a WhatsApp confirmation once verified.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">Organisation name</label>
        <input
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="e.g. Lagos Island General Hospital"
          className="w-full border border-border rounded-lg p-3 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">Organisation type</label>
        <select
          value={form.org_type}
          onChange={(e) => setForm((f) => ({ ...f, org_type: e.target.value }))}
          className="w-full border border-border rounded-lg p-3 text-sm"
        >
          <option value="">Select type</option>
          {ORG_TYPES.map((t) => (
            <option key={t} value={t}>{ORG_LABELS[t]}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-textMuted mb-1">Contact person</label>
          <input
            value={form.contact_name}
            onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
            placeholder="Full name"
            className="w-full border border-border rounded-lg p-3 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-textMuted mb-1">Contact phone</label>
          <input
            value={form.contact_phone}
            onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))}
            placeholder="+2348012345678"
            className="w-full border border-border rounded-lg p-3 text-sm"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">WhatsApp number (for incident alerts)</label>
        <input
          value={form.contact_whatsapp}
          onChange={(e) => setForm((f) => ({ ...f, contact_whatsapp: e.target.value }))}
          placeholder="+2348012345678"
          className="w-full border border-border rounded-lg p-3 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">Street address</label>
        <input
          value={form.address}
          onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
          placeholder="e.g. 12 Marina St, Lagos Island"
          className="w-full border border-border rounded-lg p-3 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">Operating hours</label>
        <input
          value={form.operating_hours}
          onChange={(e) => setForm((f) => ({ ...f, operating_hours: e.target.value }))}
          placeholder="e.g. 24/7  or  Mon–Fri 8am–6pm"
          className="w-full border border-border rounded-lg p-3 text-sm"
        />
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-2">
          Incident types you can respond to
        </label>
        <div className="flex flex-wrap gap-2">
          {INCIDENT_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => toggleIncidentType(t)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition ${
                form.responds_to.includes(t)
                  ? 'bg-primary text-white border-primary'
                  : 'bg-white text-textBody border-border hover:border-primary'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-2">
          Response radius:{' '}
          <span className="text-primary font-bold">{form.response_radius_km} km</span>
        </label>
        <div className="grid grid-cols-4 gap-2">
          {[5, 10, 20, 50].map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setForm((f) => ({ ...f, response_radius_km: r }))}
              className={`py-2 rounded-lg text-xs font-semibold border transition ${
                form.response_radius_km === r
                  ? 'bg-primary text-white border-primary'
                  : 'bg-white text-textBody border-border hover:border-primary'
              }`}
            >
              {r} km
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-semibold text-textMuted mb-1">
          Organisation location — tap map to pin
        </label>
        <div className="rounded-xl overflow-hidden border border-border mb-2" style={{ height: 180 }}>
          <MapContainer center={[6.5244, 3.3792]} zoom={12} style={{ height: '100%', width: '100%' }}>
            <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <PinPicker
              onSelect={(lat, lng) => setForm((f) => ({ ...f, location_lat: lat, location_lng: lng }))}
            />
            {form.location_lat && form.location_lng && (
              <Marker position={[form.location_lat, form.location_lng]} />
            )}
          </MapContainer>
        </div>
        <button
          type="button"
          onClick={() =>
            navigator.geolocation.getCurrentPosition((pos) =>
              setForm((f) => ({
                ...f,
                location_lat: pos.coords.latitude,
                location_lng: pos.coords.longitude,
              }))
            )
          }
          className="text-primary text-xs hover:underline"
        >
          📍 Use my current location
        </button>
      </div>

      {mut.isError && (
        <p className="text-primary text-sm">Submission failed. Please check your details and try again.</p>
      )}

      <button
        onClick={() => mut.mutate()}
        disabled={
          mut.isPending ||
          !form.name ||
          !form.org_type ||
          !form.contact_whatsapp ||
          !form.location_lat
        }
        className="w-full bg-primary text-white py-3 rounded-xl font-semibold text-sm disabled:opacity-50 hover:bg-red-700 transition"
      >
        {mut.isPending ? 'Submitting...' : 'Register Organisation'}
      </button>
    </div>
  )
}

export default function JoinPage() {
  const [responderChannel, setResponderChannel] = useState<'whatsapp' | 'web'>('whatsapp')
  const [orgChannel, setOrgChannel] = useState<'whatsapp' | 'web'>('whatsapp')

  return (
    <div className="min-h-screen bg-bg font-sans">
      <Nav />
      <div className="bg-white border-b border-border px-6 py-4">
        <h1 className="font-bold text-lg text-textPrimary">Join Siren</h1>
        <p className="text-textMuted text-sm">Register as a responder or verified organisation</p>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-textPrimary mb-3">Become part of the response</h1>
          <p className="text-textBody max-w-lg mx-auto">
            Register as a community responder or organisation. Use WhatsApp for the quickest setup,
            or fill in the web form if you prefer a browser experience — both reach the same system.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
          {/* Responder card */}
          <div className="bg-white rounded-2xl border border-border p-8">
            <div className="text-4xl mb-3">🩺</div>
            <h2 className="text-2xl font-bold text-textPrimary mb-2">Community Responder</h2>
            <p className="text-textBody text-sm mb-5">
              Receive WhatsApp alerts for emergencies that match your skills and fall within your area.
              You choose when and whether to respond — no commitment required.
            </p>

            <div className="mb-4 text-xs text-textMuted">
              <span className="font-semibold">Skills we need: </span>
              {Object.values(SKILL_LABELS).join(' · ')}
            </div>

            <ChannelToggle channel={responderChannel} onChange={setResponderChannel} />

            {responderChannel === 'whatsapp' ? (
              <div className="space-y-4">
                <p className="text-textBody text-sm">
                  Send <code className="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-sm font-bold">RESPONDER</code> to
                  Siren on WhatsApp and follow the guided prompts. Takes about 2 minutes.
                </p>
                <ol className="space-y-2 text-sm text-textBody list-none">
                  {[
                    'Send RESPONDER to start',
                    'Share your name and skill category',
                    'Share your location or area',
                    'Our team verifies and activates your account',
                  ].map((s, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="font-bold text-green-600">{i + 1}.</span> {s}
                    </li>
                  ))}
                </ol>
                <a
                  href={`https://wa.me/${WA}?text=RESPONDER`}
                  className="block text-center bg-green-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-green-700 transition"
                >
                  📱 Start on WhatsApp
                </a>
              </div>
            ) : (
              <ResponderWebForm />
            )}
          </div>

          {/* Organisation card */}
          <div className="bg-white rounded-2xl border border-border p-8">
            <div className="text-4xl mb-3">🏥</div>
            <h2 className="text-2xl font-bold text-textPrimary mb-2">Organisation</h2>
            <p className="text-textBody text-sm mb-5">
              Hospitals, clinics, ambulance services, NGOs, and government agencies — join the Siren
              verified partner network and receive proximity alerts for incidents near you.
            </p>

            <div className="mb-4 text-xs text-textMuted">
              <span className="font-semibold">Types: </span>
              {Object.values(ORG_LABELS).join(' · ')}
            </div>

            <ChannelToggle channel={orgChannel} onChange={setOrgChannel} />

            {orgChannel === 'whatsapp' ? (
              <div className="space-y-4">
                <p className="text-textBody text-sm">
                  Send <code className="bg-gray-100 px-1.5 py-0.5 rounded font-mono text-sm font-bold">REGISTER ORG</code> to
                  Siren on WhatsApp and follow the guided prompts. Takes about 3 minutes.
                </p>
                <ol className="space-y-2 text-sm text-textBody list-none">
                  {[
                    'Send REGISTER ORG to start',
                    'Share organisation name and type',
                    'Share your location and operating hours',
                    'Our team verifies and adds you to the network',
                  ].map((s, i) => (
                    <li key={i} className="flex gap-2">
                      <span className="font-bold text-green-600">{i + 1}.</span> {s}
                    </li>
                  ))}
                </ol>
                <a
                  href={`https://wa.me/${WA}?text=REGISTER+ORG`}
                  className="block text-center bg-green-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-green-700 transition"
                >
                  📱 Start on WhatsApp
                </a>
              </div>
            ) : (
              <OrgWebForm />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
