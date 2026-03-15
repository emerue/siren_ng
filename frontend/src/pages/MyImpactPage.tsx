import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'
import { getMyImpact } from '../api'
import type { MyImpactData } from '../types'

const WHATSAPP_NUMBER = import.meta.env.VITE_WHATSAPP_NUMBER || '+2349000000000'

export default function MyImpactPage() {
  const [params] = useSearchParams()
  const phoneHash = params.get('phone_hash') || ''

  const { data, isLoading, isError } = useQuery<MyImpactData>({
    queryKey: ['my-impact', phoneHash],
    queryFn: () => getMyImpact(phoneHash),
    enabled: !!phoneHash,
  })

  if (!phoneHash) {
    return (
      <div className="min-h-screen bg-bg font-sans flex items-center justify-center">
        <div className="text-center p-8">
          <h1 className="text-2xl font-bold mb-4">My Impact</h1>
          <p className="text-textBody">No phone hash provided. Open this link from WhatsApp.</p>
          <a
            href={`https://wa.me/${WHATSAPP_NUMBER.replace('+', '')}?text=MY IMPACT`}
            className="mt-4 inline-block bg-primary text-white px-6 py-2 rounded-lg font-semibold"
          >
            Send MY IMPACT to Siren
          </a>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-bg font-sans flex items-center justify-center">
        <p className="text-textBody">Loading your impact data...</p>
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="min-h-screen bg-bg font-sans flex items-center justify-center">
        <div className="text-center p-8">
          <p className="text-textBody">No impact data found. Start by sending WATCH to Siren.</p>
          <a
            href={`https://wa.me/${WHATSAPP_NUMBER.replace('+', '')}?text=WATCH`}
            className="mt-4 inline-block bg-primary text-white px-6 py-2 rounded-lg font-semibold"
          >
            Get started
          </a>
        </div>
      </div>
    )
  }

  const shareText = `I protect ${data.subscriptions.length} Lagos location${data.subscriptions.length !== 1 ? 's' : ''} with Siren.ng. Join me: siren.ng`

  return (
    <div className="min-h-screen bg-bg font-sans">
      <div className="bg-primary text-white px-6 py-4">
        <h1 className="font-bold text-lg">My Impact</h1>
        <p className="text-white/80 text-sm">Your community safety contribution</p>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">

        {/* Impact stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-xl border border-border p-4 text-center">
            <div className="text-3xl font-bold text-primary">{data.total_alerts_received}</div>
            <div className="text-xs text-textMuted mt-1">Alerts received</div>
          </div>
          <div className="bg-white rounded-xl border border-border p-4 text-center">
            <div className="text-3xl font-bold text-primary">{data.incidents_near_count}</div>
            <div className="text-xs text-textMuted mt-1">Incidents near you</div>
          </div>
          <div className="bg-white rounded-xl border border-border p-4 text-center">
            <div className="text-3xl font-bold text-primary">{data.incidents_resolved_near}</div>
            <div className="text-xs text-textMuted mt-1">Resolved nearby</div>
          </div>
          <div className="bg-white rounded-xl border border-border p-4 text-center">
            <div className="text-3xl font-bold text-primary">{data.responders_triggered_count}</div>
            <div className="text-xs text-textMuted mt-1">Responders triggered</div>
          </div>
        </div>

        {data.total_donations_on_alerted_incidents > 0 && (
          <div className="bg-white rounded-xl border border-border p-4 text-center">
            <div className="text-2xl font-bold text-success">
              &#8358;{data.total_donations_on_alerted_incidents.toLocaleString()}
            </div>
            <div className="text-xs text-textMuted mt-1">Community donated on incidents near your locations</div>
          </div>
        )}

        {/* Per-location safety scores */}
        {data.subscriptions.map((sub) => (
          <div key={sub.id} className="bg-white rounded-xl border border-border p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="font-bold text-textPrimary">{sub.label}</h3>
                <div className="text-xs text-textMuted">{sub.subscription_type} · {sub.is_active ? 'Active' : 'Paused'}</div>
              </div>
              <div className="text-right">
                <div className={`text-3xl font-bold ${sub.safety_score >= 80 ? 'text-success' : sub.safety_score >= 50 ? 'text-amber-600' : 'text-primary'}`}>
                  {sub.safety_score}
                </div>
                <div className="text-xs text-textMuted">Safety score</div>
              </div>
            </div>

            {sub.score_logs.length > 1 && (
              <div style={{ height: 120 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={[...sub.score_logs].reverse().map((log) => ({
                    date: format(new Date(log.created_at), 'MMM d'),
                    score: log.score,
                  }))}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E8" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="score" stroke="#C0392B" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        ))}

        {/* Shareable card */}
        <div className="bg-primary text-white rounded-xl p-5">
          <p className="font-bold text-lg mb-1">
            I protect {data.subscriptions.length} Lagos location{data.subscriptions.length !== 1 ? 's' : ''} with Siren.ng
          </p>
          <p className="text-white/80 text-sm mb-4">Join the community keeping Lagos safer.</p>
          <div className="flex gap-2 flex-wrap">
            <a
              href={`https://wa.me/?text=${encodeURIComponent(shareText)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-white text-primary px-4 py-2 rounded-lg text-sm font-semibold"
            >
              Share on WhatsApp
            </a>
            <button
              onClick={() => navigator.clipboard.writeText(shareText)}
              className="bg-white/20 text-white px-4 py-2 rounded-lg text-sm font-semibold"
            >
              Copy link
            </button>
          </div>
        </div>

      </div>
    </div>
  )
}
