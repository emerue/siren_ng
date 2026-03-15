import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { getActiveIncidents, getAnalyticsSummary, dispatchIncident, resolveIncident } from '../api'
import { useWebSocket } from '../hooks/useWebSocket'
import { useIncidentStore } from '../store/incidentStore'
import DashboardLayout from '../components/DashboardLayout'
import type { Incident } from '../types'
import { useEffect } from 'react'

function SeverityBadge({ s }: { s: string }) {
  const c: Record<string, string> = { CRITICAL: 'bg-red-600 text-white', HIGH: 'bg-red-400 text-white', MEDIUM: 'bg-amber-400 text-white', LOW: 'bg-yellow-200 text-gray-700' }
  return <span className={`text-xs font-bold px-2 py-0.5 rounded ${c[s] || ''}`}>{s}</span>
}

export default function DashboardHome() {
  useWebSocket()
  const qc = useQueryClient()
  const { incidents, setIncidents } = useIncidentStore()

  const { data: active } = useQuery<Incident[]>({ queryKey: ['active-incidents'], queryFn: getActiveIncidents, refetchInterval: 15_000 })
  const { data: summary } = useQuery({ queryKey: ['analytics-summary'], queryFn: () => getAnalyticsSummary('7d'), refetchInterval: 60_000 })

  useEffect(() => { if (active) setIncidents(active) }, [active, setIncidents])

  const dispatchMut = useMutation({
    mutationFn: (id: string) => dispatchIncident(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['active-incidents'] }),
  })
  const resolveMut = useMutation({
    mutationFn: (id: string) => resolveIncident(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['active-incidents'] }),
  })

  return (
    <DashboardLayout>
      <div className="p-8">
        <h1 className="text-2xl font-bold text-textPrimary mb-6">Dashboard</h1>

        {/* Stat cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Active Incidents', value: summary.active_incidents },
              { label: "Today's Total", value: summary.today_total },
              { label: 'Responders Available', value: summary.responders_available },
              { label: 'Donated Today', value: `₦${(summary.total_donated_today_naira || 0).toLocaleString()}` },
            ].map((stat) => (
              <div key={stat.label} className="bg-white rounded-xl border border-border p-5">
                <div className="text-2xl font-bold text-textPrimary">{stat.value}</div>
                <div className="text-textMuted text-sm">{stat.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Active incidents table */}
        <div className="bg-white rounded-xl border border-border">
          <div className="px-6 py-4 border-b border-border font-semibold text-textPrimary">
            Active Incidents ({incidents.length})
          </div>
          {incidents.length === 0 && (
            <p className="text-textMuted text-center py-8 text-sm">No active incidents.</p>
          )}
          <div className="divide-y divide-border">
            {incidents.map((inc) => (
              <div key={inc.id} className="px-6 py-4 flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <SeverityBadge s={inc.severity} />
                    <span className="font-medium text-textPrimary text-sm">{inc.incident_type}</span>
                    <span className="text-textMuted text-xs">{inc.zone_name}</span>
                  </div>
                  <p className="text-textBody text-xs truncate">{inc.description}</p>
                  <div className="text-textMuted text-xs mt-0.5">
                    {formatDistanceToNow(new Date(inc.created_at), { addSuffix: true })} ·
                    AI: {(inc.ai_confidence * 100).toFixed(0)}% ·
                    {inc.vouch_count} vouches
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Link to={`/dashboard/incidents/${inc.id}`} className="text-xs border border-border px-2 py-1 rounded hover:border-primary">
                    View
                  </Link>
                  <button
                    onClick={() => dispatchMut.mutate(inc.id)}
                    className="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700"
                  >
                    Dispatch
                  </button>
                  <button
                    onClick={() => resolveMut.mutate(inc.id)}
                    className="text-xs bg-success text-white px-2 py-1 rounded hover:bg-green-800"
                  >
                    Resolve
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}
