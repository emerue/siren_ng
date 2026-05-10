import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const API = import.meta.env.VITE_API_BASE_URL || ''

interface Subscription {
  id: number
  lga: string
  whatsapp_number: string
  is_active: boolean
  created_at: string
}

export default function GuardianModePage() {
  const token = useAuthStore((s) => s.token)
  const navigate = useNavigate()

  const [availableLGAs, setAvailableLGAs] = useState<string[]>([])
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState<string | null>(null)
  const [whatsappNumber, setWhatsappNumber] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      navigate('/login')
      return
    }
    fetchData()
  }, [token])

  const authHeaders = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  }

  const fetchData = async () => {
    setLoading(true)
    try {
      const [lgasRes, subsRes] = await Promise.all([
        fetch(`${API}/api/subscriptions/lga/available_lgas/`, { headers: authHeaders }),
        fetch(`${API}/api/subscriptions/lga/`, { headers: authHeaders }),
      ])
      const lgasData = await lgasRes.json()
      const subsData = await subsRes.json()
      setAvailableLGAs(lgasData.lgas || [])
      setSubscriptions(Array.isArray(subsData) ? subsData : [])
    } catch {
      setError('Failed to load data. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const activeSub = (lga: string) =>
    subscriptions.find((s) => s.lga === lga && s.is_active)

  const handleToggle = async (lga: string) => {
    setToggling(lga)
    setError('')
    const existing = activeSub(lga)

    try {
      if (existing) {
        await fetch(`${API}/api/subscriptions/lga/${existing.id}/`, {
          method: 'DELETE',
          headers: authHeaders,
        })
      } else {
        const body: Record<string, string> = { lga }
        if (whatsappNumber.trim()) body.whatsapp_number = whatsappNumber.trim()
        await fetch(`${API}/api/subscriptions/lga/`, {
          method: 'POST',
          headers: authHeaders,
          body: JSON.stringify(body),
        })
      }
      await fetchData()
    } catch {
      setError('Action failed. Please try again.')
    } finally {
      setToggling(null)
    }
  }

  const activeCount = subscriptions.filter((s) => s.is_active).length

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">Loading Guardian Mode...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate(-1)}
            className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-block"
          >
            ← Back
          </button>
          <h1 className="text-3xl font-bold text-gray-900">Guardian Mode</h1>
          <p className="text-gray-600 mt-1">
            Get WhatsApp alerts when emergencies happen in your Lagos LGAs.
          </p>
          {activeCount > 0 && (
            <p className="mt-2 text-sm text-green-700 font-medium">
              Active: {activeCount} LGA{activeCount !== 1 ? 's' : ''} watched
            </p>
          )}
        </div>

        {/* WhatsApp number input */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Your WhatsApp number (for alerts)
          </label>
          <input
            type="tel"
            value={whatsappNumber}
            onChange={(e) => setWhatsappNumber(e.target.value)}
            placeholder="+2348012345678"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
          />
          <p className="text-xs text-gray-400 mt-1">
            Used when subscribing to a new LGA. Leave blank to update later.
          </p>
        </div>

        {error && (
          <p className="text-red-600 text-sm mb-4 bg-red-50 p-3 rounded-lg">{error}</p>
        )}

        {/* LGA grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-8">
          {availableLGAs.map((lga) => {
            const subscribed = !!activeSub(lga)
            const busy = toggling === lga
            return (
              <button
                key={lga}
                onClick={() => handleToggle(lga)}
                disabled={busy}
                className={`
                  flex items-center gap-3 p-4 rounded-xl border-2 text-left transition-all
                  ${subscribed
                    ? 'border-red-500 bg-red-50 text-red-900'
                    : 'border-gray-200 bg-white text-gray-800 hover:border-gray-300'
                  }
                  ${busy ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                `}
              >
                <span
                  className={`
                    w-5 h-5 rounded flex-shrink-0 border-2 flex items-center justify-center text-xs
                    ${subscribed ? 'border-red-500 bg-red-500 text-white' : 'border-gray-300'}
                  `}
                >
                  {subscribed && '✓'}
                </span>
                <span className="font-medium text-sm">{lga}</span>
              </button>
            )
          })}
        </div>

        {/* Info box */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-sm text-blue-800">
          <p className="font-semibold mb-2">How it works</p>
          <ul className="space-y-1">
            <li>✓ Select the LGAs where you live, work, or have family</li>
            <li>✓ When an emergency is verified in that LGA, you get a WhatsApp alert</li>
            <li>✓ Only verified incidents trigger alerts — no false alarms</li>
            <li>✓ Unsubscribe anytime by unchecking the LGA</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
