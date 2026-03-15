import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { useMutation } from '@tanstack/react-query'
import { webIngest } from '../api'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const TYPES = [
  { value: 'FIRE', icon: '🔥', label: 'Fire' },
  { value: 'FLOOD', icon: '🌊', label: 'Flood' },
  { value: 'COLLAPSE', icon: '🏚', label: 'Collapse' },
  { value: 'RTA', icon: '🚗', label: 'Road Accident' },
  { value: 'EXPLOSION', icon: '💥', label: 'Explosion' },
  { value: 'DROWNING', icon: '🆘', label: 'Drowning' },
  { value: 'HAZARD', icon: '⚡', label: 'Hazard' },
]

function LocationPicker({ onSelect }: { onSelect: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) { onSelect(e.latlng.lat, e.latlng.lng) },
  })
  return null
}

export default function ReportPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState({
    incident_type: '',
    location_lat: null as number | null,
    location_lng: null as number | null,
    address_text: '',
    description: '',
  })

  const submitMut = useMutation({
    mutationFn: () => webIngest(form),
    onSuccess: (data) => navigate(`/track/${data.id}`),
  })

  return (
    <div className="min-h-screen bg-bg font-sans">
      <div className="bg-primary text-white px-6 py-4">
        <h1 className="font-bold text-lg">Report an Emergency</h1>
        <p className="text-white/80 text-sm">No account needed · Usually processed in 90 seconds</p>
      </div>

      <div className="max-w-lg mx-auto px-4 py-6">
        {/* Progress */}
        <div className="flex gap-2 mb-6">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className={`flex-1 h-1.5 rounded-full ${s <= step ? 'bg-primary' : 'bg-border'}`} />
          ))}
        </div>

        {/* Step 1: Type */}
        {step === 1 && (
          <div>
            <h2 className="font-bold text-xl mb-4 text-textPrimary">What type of emergency?</h2>
            <div className="grid grid-cols-2 gap-3">
              {TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => { setForm((f) => ({ ...f, incident_type: t.value })); setStep(2) }}
                  className={`p-4 rounded-xl border text-left transition ${form.incident_type === t.value ? 'border-primary bg-red-50' : 'border-border bg-white hover:border-primary'}`}
                >
                  <div className="text-3xl mb-1">{t.icon}</div>
                  <div className="font-medium text-textPrimary text-sm">{t.label}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Location */}
        {step === 2 && (
          <div>
            <h2 className="font-bold text-xl mb-4 text-textPrimary">Where is it happening?</h2>
            <button
              onClick={() => {
                navigator.geolocation.getCurrentPosition((pos) => {
                  setForm((f) => ({ ...f, location_lat: pos.coords.latitude, location_lng: pos.coords.longitude }))
                })
              }}
              className="w-full mb-3 border border-border bg-white rounded-lg p-3 text-sm text-left hover:border-primary flex items-center gap-2"
            >
              📍 Use my current location
            </button>
            <div className="rounded-xl overflow-hidden border border-border mb-3" style={{ height: 200 }}>
              <MapContainer
                center={[form.location_lat || 6.5244, form.location_lng || 3.3792]}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
              >
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <LocationPicker onSelect={(lat, lng) => setForm((f) => ({ ...f, location_lat: lat, location_lng: lng }))} />
                {form.location_lat && form.location_lng && (
                  <Marker position={[form.location_lat, form.location_lng]} />
                )}
              </MapContainer>
            </div>
            <input
              value={form.address_text}
              onChange={(e) => setForm((f) => ({ ...f, address_text: e.target.value }))}
              placeholder="Street address or landmark (optional)"
              className="w-full border border-border rounded-lg p-3 text-sm mb-4"
            />
            <div className="flex gap-2">
              <button onClick={() => setStep(1)} className="flex-1 border border-border py-3 rounded-lg text-sm">Back</button>
              <button onClick={() => setStep(3)} className="flex-1 bg-primary text-white py-3 rounded-lg text-sm font-semibold">Next</button>
            </div>
          </div>
        )}

        {/* Step 3: Description */}
        {step === 3 && (
          <div>
            <h2 className="font-bold text-xl mb-4 text-textPrimary">What are you seeing?</h2>
            <textarea
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value.slice(0, 500) }))}
              placeholder="Describe what you see. The more detail, the faster AI can verify it."
              rows={5}
              className="w-full border border-border rounded-lg p-3 text-sm mb-1 resize-none"
            />
            <p className="text-textMuted text-xs mb-4">{form.description.length}/500</p>
            <div className="flex gap-2">
              <button onClick={() => setStep(2)} className="flex-1 border border-border py-3 rounded-lg text-sm">Back</button>
              <button
                onClick={() => setStep(4)}
                disabled={form.description.length < 5}
                className="flex-1 bg-primary text-white py-3 rounded-lg text-sm font-semibold disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Submit */}
        {step === 4 && (
          <div>
            <h2 className="font-bold text-xl mb-4 text-textPrimary">Ready to submit</h2>
            <div className="bg-white rounded-xl border border-border p-4 mb-4 space-y-2 text-sm">
              <div><span className="text-textMuted">Type: </span>{form.incident_type}</div>
              <div><span className="text-textMuted">Location: </span>{form.address_text || (form.location_lat ? `${form.location_lat.toFixed(4)}, ${form.location_lng?.toFixed(4)}` : 'Not set')}</div>
              <div><span className="text-textMuted">Description: </span>{form.description}</div>
            </div>
            {submitMut.isError && (
              <p className="text-primary text-sm mb-3">Submission failed. Please try again.</p>
            )}
            <div className="flex gap-2">
              <button onClick={() => setStep(3)} className="flex-1 border border-border py-3 rounded-lg text-sm">Back</button>
              <button
                onClick={() => submitMut.mutate()}
                disabled={submitMut.isPending || !form.description}
                className="flex-1 bg-primary text-white py-3 rounded-lg text-sm font-semibold disabled:opacity-50"
              >
                {submitMut.isPending ? 'Submitting...' : '🚨 Submit Report'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
