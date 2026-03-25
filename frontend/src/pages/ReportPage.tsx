import { useState, useRef, useCallback } from 'react'
import Nav from '../components/Nav'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet'
import L from 'leaflet'
import { useMutation } from '@tanstack/react-query'
import { webIngest, uploadMedia } from '../api'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

const TYPES = [
  { value: 'FIRE',      icon: '🔥', label: 'Fire',          desc: 'Building or bush fire' },
  { value: 'FLOOD',     icon: '🌊', label: 'Flood',         desc: 'Flooding or water surge' },
  { value: 'COLLAPSE',  icon: '🏚', label: 'Collapse',      desc: 'Building or structural' },
  { value: 'RTA',       icon: '🚗', label: 'Road Accident', desc: 'Vehicle crash or blockage' },
  { value: 'EXPLOSION', icon: '💥', label: 'Explosion',     desc: 'Gas or chemical blast' },
  { value: 'DROWNING',  icon: '🆘', label: 'Drowning',      desc: 'Water emergency' },
  { value: 'HAZARD',    icon: '⚡', label: 'Hazard',        desc: 'Exposed wires or structural risk' },
]

const STEPS = ['Type', 'Location', 'Details', 'Photos', 'Submit']

const IMAGE_MAX = 5 * 1024 * 1024
const VIDEO_MAX = 50 * 1024 * 1024

function LocationPicker({ onSelect }: { onSelect: (lat: number, lng: number) => void }) {
  useMapEvents({ click(e) { onSelect(e.latlng.lat, e.latlng.lng) } })
  return null
}

function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1.5 mb-8">
      {STEPS.map((label, i) => {
        const n = i + 1
        const done = n < current
        const active = n === current
        return (
          <div key={label} className="flex items-center gap-1.5 flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                done   ? 'bg-success text-white' :
                active ? 'bg-primary text-white ring-4 ring-red-100' :
                         'bg-border text-textMuted'
              }`}>
                {done ? '✓' : n}
              </div>
              <span className={`text-[10px] font-medium ${active ? 'text-primary' : done ? 'text-success' : 'text-textMuted'}`}>
                {label}
              </span>
            </div>
            {i < total - 1 && (
              <div className={`flex-1 h-0.5 mb-3 rounded ${done ? 'bg-success' : 'bg-border'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function FilePreview({ file, onRemove }: { file: File; onRemove: () => void }) {
  const isImage = file.type.startsWith('image/')
  const sizeMB = (file.size / (1024 * 1024)).toFixed(1)
  const [preview] = useState(() => isImage ? URL.createObjectURL(file) : null)

  return (
    <div className="flex items-center gap-3 bg-white rounded-xl border border-border p-3 group">
      {isImage && preview ? (
        <img src={preview} alt="" className="w-14 h-14 rounded-lg object-cover shrink-0" />
      ) : (
        <div className="w-14 h-14 rounded-lg bg-gray-100 flex items-center justify-center text-2xl shrink-0">🎬</div>
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-textPrimary truncate">{file.name}</p>
        <p className="text-xs text-textMuted mt-0.5">{sizeMB} MB · {isImage ? 'Image' : 'Video'}</p>
      </div>
      <button
        onClick={onRemove}
        className="w-7 h-7 rounded-full flex items-center justify-center text-textMuted hover:bg-red-50 hover:text-primary transition opacity-0 group-hover:opacity-100"
      >
        ×
      </button>
    </div>
  )
}

export default function ReportPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [step, setStep] = useState(1)
  const [dragOver, setDragOver] = useState(false)
  const [fileErrors, setFileErrors] = useState<string[]>([])
  const [mediaFiles, setMediaFiles] = useState<File[]>([])
  const [uploadProgress, setUploadProgress] = useState<string>('')
  const [form, setForm] = useState({
    incident_type: '',
    location_lat: null as number | null,
    location_lng: null as number | null,
    address_text: '',
    description: '',
  })

  const validateAndAddFiles = useCallback((incoming: File[]) => {
    const errors: string[] = []
    const valid: File[] = []
    const allowed = ['image/jpeg', 'image/png', 'image/webp', 'video/mp4', 'video/quicktime']

    for (const f of incoming) {
      if (!allowed.includes(f.type)) {
        errors.push(`${f.name}: unsupported type`)
        continue
      }
      const limit = f.type.startsWith('video') ? VIDEO_MAX : IMAGE_MAX
      if (f.size > limit) {
        const mb = limit / (1024 * 1024)
        errors.push(`${f.name}: exceeds ${mb}MB limit`)
        continue
      }
      valid.push(f)
    }

    setMediaFiles(prev => {
      const combined = [...prev, ...valid]
      if (combined.length > 5) {
        errors.push('Max 5 files allowed — some were not added.')
        return combined.slice(0, 5)
      }
      return combined
    })
    setFileErrors(errors)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    validateAndAddFiles(Array.from(e.dataTransfer.files))
  }, [validateAndAddFiles])

  const submitMut = useMutation({
    mutationFn: async () => {
      setUploadProgress('Creating report...')
      const incident = await webIngest(form)
      const incidentId = incident.id

      if (mediaFiles.length > 0) {
        for (let i = 0; i < mediaFiles.length; i++) {
          setUploadProgress(`Uploading ${i + 1}/${mediaFiles.length} files...`)
          try {
            await uploadMedia(incidentId, mediaFiles[i])
          } catch {
            // Don't block navigation on media upload failure
          }
        }
      }
      setUploadProgress('')
      return incident
    },
    onSuccess: (data) => navigate(`/track/${data.id}`),
  })

  const selectedType = TYPES.find(t => t.value === form.incident_type)

  return (
    <div className="min-h-screen bg-bg font-sans">
      <Nav />
      {/* Header */}
      <div className="bg-white border-b border-border sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4 flex items-center gap-3">
          <button onClick={() => step > 1 ? setStep(s => s - 1) : navigate('/')}
            className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-gray-100 transition text-textBody">
            ←
          </button>
          <div>
            <h1 className="font-bold text-textPrimary leading-tight">Report Emergency</h1>
            <p className="text-xs text-textMuted">No account needed · AI verifies in ~90s</p>
          </div>
          <div className="ml-auto">
            <span className="text-xs text-textMuted font-medium">{step}/5</span>
          </div>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 pt-6 pb-24">
        <StepIndicator current={step} total={5} />

        {/* Step 1: Type */}
        {step === 1 && (
          <div className="animate-in fade-in duration-200">
            <h2 className="text-2xl font-bold text-textPrimary mb-1">What is happening?</h2>
            <p className="text-textMuted text-sm mb-6">Select the emergency type that best matches.</p>
            <div className="grid grid-cols-2 gap-3">
              {TYPES.map((t) => (
                <button
                  key={t.value}
                  onClick={() => { setForm(f => ({ ...f, incident_type: t.value })); setStep(2) }}
                  className={`p-4 rounded-2xl border-2 text-left transition-all hover:shadow-sm active:scale-95 ${
                    form.incident_type === t.value
                      ? 'border-primary bg-red-50 shadow-sm'
                      : 'border-border bg-white hover:border-primary/40'
                  }`}
                >
                  <div className="text-3xl mb-2">{t.icon}</div>
                  <div className="font-semibold text-textPrimary text-sm">{t.label}</div>
                  <div className="text-textMuted text-xs mt-0.5">{t.desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Location */}
        {step === 2 && (
          <div className="animate-in fade-in duration-200">
            <h2 className="text-2xl font-bold text-textPrimary mb-1">Where is it?</h2>
            <p className="text-textMuted text-sm mb-6">Tap the map or use your GPS location.</p>

            <button
              onClick={() => navigator.geolocation.getCurrentPosition(
                pos => setForm(f => ({ ...f, location_lat: pos.coords.latitude, location_lng: pos.coords.longitude })),
                () => alert('Location access denied. Please tap the map instead.')
              )}
              className="w-full mb-4 border-2 border-dashed border-primary/30 bg-red-50 rounded-xl p-3 text-sm font-medium text-primary flex items-center gap-2 hover:border-primary/60 transition"
            >
              <span className="text-lg">📍</span>
              Use my current GPS location
              {form.location_lat && <span className="ml-auto text-xs bg-primary text-white px-2 py-0.5 rounded-full">Set ✓</span>}
            </button>

            <div className="rounded-2xl overflow-hidden border-2 border-border mb-4 shadow-sm" style={{ height: 220 }}>
              <MapContainer
                center={[form.location_lat ?? 6.5244, form.location_lng ?? 3.3792]}
                zoom={13}
                style={{ height: '100%', width: '100%' }}
              >
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                <LocationPicker onSelect={(lat, lng) => setForm(f => ({ ...f, location_lat: lat, location_lng: lng }))} />
                {form.location_lat && form.location_lng && (
                  <Marker position={[form.location_lat, form.location_lng]} />
                )}
              </MapContainer>
            </div>

            <input
              value={form.address_text}
              onChange={e => setForm(f => ({ ...f, address_text: e.target.value }))}
              placeholder="Street address or nearby landmark (optional)"
              className="w-full border border-border rounded-xl p-3 text-sm focus:outline-none focus:border-primary transition mb-6"
            />

            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="flex-1 border border-border py-3 rounded-xl text-sm font-medium hover:bg-gray-50 transition">Back</button>
              <button onClick={() => setStep(3)} className="flex-1 bg-primary text-white py-3 rounded-xl text-sm font-semibold hover:bg-red-700 transition">Next →</button>
            </div>
          </div>
        )}

        {/* Step 3: Description */}
        {step === 3 && (
          <div className="animate-in fade-in duration-200">
            <h2 className="text-2xl font-bold text-textPrimary mb-1">What are you seeing?</h2>
            <p className="text-textMuted text-sm mb-6">
              Be specific — include number of people affected, fire size, vehicle count, etc. This helps AI verify faster.
            </p>

            <div className="relative mb-2">
              <textarea
                value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value.slice(0, 500) }))}
                placeholder="e.g. Large fire at a 3-storey building. Flames visible from 3rd floor. About 10 people evacuating on the street. No injuries seen yet."
                rows={6}
                className="w-full border border-border rounded-xl p-4 text-sm focus:outline-none focus:border-primary transition resize-none"
              />
              <span className="absolute bottom-3 right-3 text-xs text-textMuted">
                {form.description.length}/500
              </span>
            </div>

            {form.description.length < 20 && form.description.length > 0 && (
              <p className="text-amber-600 text-xs mb-4">More detail helps AI verify your report faster.</p>
            )}

            <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 mb-6 text-xs text-blue-700">
              💡 Tip: Mention location landmarks, number of people, and what you can see right now.
            </div>

            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="flex-1 border border-border py-3 rounded-xl text-sm font-medium hover:bg-gray-50 transition">Back</button>
              <button
                onClick={() => setStep(4)}
                disabled={form.description.length < 5}
                className="flex-1 bg-primary text-white py-3 rounded-xl text-sm font-semibold disabled:opacity-40 hover:bg-red-700 transition"
              >
                Next →
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Media */}
        {step === 4 && (
          <div className="animate-in fade-in duration-200">
            <h2 className="text-2xl font-bold text-textPrimary mb-1">Add photos or video</h2>
            <p className="text-textMuted text-sm mb-6">
              Optional but powerful — visual evidence speeds up AI verification and helps responders prepare.
            </p>

            {/* Drop zone */}
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all ${
                dragOver
                  ? 'border-primary bg-red-50 scale-[1.01]'
                  : 'border-border bg-white hover:border-primary/50 hover:bg-gray-50'
              }`}
            >
              <div className="text-4xl mb-3">📸</div>
              <p className="font-semibold text-textPrimary">
                {dragOver ? 'Drop files here' : 'Click to select or drag files'}
              </p>
              <p className="text-textMuted text-xs mt-2 leading-relaxed">
                Up to 5 files · Photos: JPG, PNG, WebP (max 5MB each)<br />
                Video: MP4, MOV (max 50MB)
              </p>
              {mediaFiles.length > 0 && (
                <div className="absolute top-3 right-3 bg-primary text-white text-xs font-bold px-2 py-0.5 rounded-full">
                  {mediaFiles.length}/5
                </div>
              )}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,.jpg,.jpeg,.png,.webp,.mp4,.mov"
                className="hidden"
                onChange={e => { validateAndAddFiles(Array.from(e.target.files ?? [])); e.target.value = '' }}
              />
            </div>

            {/* Errors */}
            {fileErrors.length > 0 && (
              <div className="mt-3 bg-red-50 border border-red-200 rounded-xl p-3">
                {fileErrors.map((e, i) => (
                  <p key={i} className="text-xs text-red-700">{e}</p>
                ))}
              </div>
            )}

            {/* Previews */}
            {mediaFiles.length > 0 && (
              <div className="mt-4 space-y-2">
                {mediaFiles.map((file, i) => (
                  <FilePreview
                    key={i}
                    file={file}
                    onRemove={() => setMediaFiles(prev => prev.filter((_, j) => j !== i))}
                  />
                ))}
              </div>
            )}

            <p className="text-center text-xs text-textMuted mt-4">
              Files are stored securely and only visible to responders and admins.
            </p>

            <div className="flex gap-3 mt-6">
              <button onClick={() => setStep(3)} className="flex-1 border border-border py-3 rounded-xl text-sm font-medium hover:bg-gray-50 transition">Back</button>
              <button onClick={() => setStep(5)} className="flex-1 bg-primary text-white py-3 rounded-xl text-sm font-semibold hover:bg-red-700 transition">
                {mediaFiles.length > 0 ? `Next (${mediaFiles.length} file${mediaFiles.length > 1 ? 's' : ''})` : 'Skip →'}
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Review */}
        {step === 5 && (
          <div className="animate-in fade-in duration-200">
            <h2 className="text-2xl font-bold text-textPrimary mb-1">Ready to submit</h2>
            <p className="text-textMuted text-sm mb-6">Review your report before sending.</p>

            <div className="bg-white rounded-2xl border border-border overflow-hidden mb-6">
              <div className="p-5 border-b border-border">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{selectedType?.icon}</span>
                  <div>
                    <p className="font-semibold text-textPrimary">{selectedType?.label}</p>
                    <p className="text-xs text-textMuted">Emergency type</p>
                  </div>
                </div>
              </div>

              <div className="p-5 border-b border-border">
                <p className="text-xs text-textMuted uppercase tracking-wide font-semibold mb-1">Location</p>
                <p className="text-sm text-textBody">
                  {form.address_text || (form.location_lat
                    ? `${form.location_lat.toFixed(5)}, ${form.location_lng?.toFixed(5)}`
                    : 'Not set')}
                </p>
              </div>

              <div className="p-5 border-b border-border">
                <p className="text-xs text-textMuted uppercase tracking-wide font-semibold mb-1">Description</p>
                <p className="text-sm text-textBody leading-relaxed">{form.description}</p>
              </div>

              <div className="p-5">
                <p className="text-xs text-textMuted uppercase tracking-wide font-semibold mb-1">Media</p>
                {mediaFiles.length > 0 ? (
                  <p className="text-sm text-textBody">{mediaFiles.length} file{mediaFiles.length > 1 ? 's' : ''} attached</p>
                ) : (
                  <p className="text-sm text-textMuted">No media attached</p>
                )}
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 text-sm text-amber-800">
              <strong>False reports are automatically detected and rejected.</strong> Submitting false reports may result in reduced trust scores.
            </div>

            {submitMut.isError && (
              <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4 text-sm text-red-700">
                Submission failed. Check your connection and try again.
              </div>
            )}

            {uploadProgress && (
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-4 flex items-center gap-3">
                <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin shrink-0"></div>
                <span className="text-sm text-blue-700">{uploadProgress}</span>
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={() => setStep(4)} className="flex-1 border border-border py-3 rounded-xl text-sm font-medium hover:bg-gray-50 transition">Back</button>
              <button
                onClick={() => submitMut.mutate()}
                disabled={submitMut.isPending || !form.description || !form.incident_type}
                className="flex-1 bg-primary text-white py-3.5 rounded-xl text-sm font-bold disabled:opacity-40 hover:bg-red-700 transition active:scale-95"
              >
                {submitMut.isPending ? '...' : '🚨 Submit Emergency Report'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
