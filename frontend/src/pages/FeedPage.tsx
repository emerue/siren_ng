import { useState } from 'react'
import Nav from '../components/Nav'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { getIncidents, vouchIncident } from '../api'
import type { Incident } from '../types'

function SeverityBadge({ severity }: { severity: string }) {
  const c: Record<string, string> = { CRITICAL: 'bg-red-600 text-white', HIGH: 'bg-red-500 text-white', MEDIUM: 'bg-amber-500 text-white', LOW: 'bg-yellow-200 text-gray-800' }
  return <span className={`text-xs font-bold px-2 py-0.5 rounded ${c[severity] || 'bg-gray-200 text-gray-600'}`}>{severity}</span>
}

function StatusBadge({ status }: { status: string }) {
  const c: Record<string, string> = { VERIFIED: 'bg-blue-100 text-blue-800', RESPONDING: 'bg-green-100 text-green-800', VERIFYING: 'bg-yellow-100 text-amber-700', RESOLVED: 'bg-green-100 text-green-800', AGENCY_NOTIFIED: 'bg-purple-100 text-purple-800' }
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${c[status] || 'bg-gray-100 text-gray-500'}`}>{status.replace('_', ' ')}</span>
}

export default function FeedPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ zone_name: '', incident_type: '', severity: '', status: '' })

  const params = Object.fromEntries(
    Object.entries({ ...filters, page: String(page) }).filter(([, v]) => v)
  )

  const { data, isLoading } = useQuery({
    queryKey: ['incidents', params],
    queryFn: () => getIncidents(params),
  })

  const incidents: Incident[] = data?.results || []
  const hasNext = !!data?.next

  const qc = useQueryClient()
  const vouchMut = useMutation({
    mutationFn: (id: string) => vouchIncident(id, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incidents'] }),
  })

  return (
    <div className="min-h-screen bg-bg font-sans">
      <Nav />

      {/* Filters */}
      <div className="max-w-2xl mx-auto px-4 py-4 flex flex-wrap gap-2">
        {[
          { key: 'incident_type', options: ['', 'FIRE', 'FLOOD', 'COLLAPSE', 'RTA', 'EXPLOSION', 'DROWNING', 'HAZARD'], label: 'Type' },
          { key: 'severity', options: ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'], label: 'Severity' },
          { key: 'status', options: ['', 'VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED'], label: 'Status' },
        ].map(({ key, options, label }) => (
          <select
            key={key}
            value={filters[key as keyof typeof filters]}
            onChange={(e) => { setFilters((f) => ({ ...f, [key]: e.target.value })); setPage(1) }}
            className="border border-border rounded-lg px-3 py-1.5 text-sm text-textBody"
          >
            <option value="">{label}: All</option>
            {options.slice(1).map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        ))}
        <input
          placeholder="Zone"
          value={filters.zone_name}
          onChange={(e) => { setFilters((f) => ({ ...f, zone_name: e.target.value })); setPage(1) }}
          className="border border-border rounded-lg px-3 py-1.5 text-sm w-28"
        />
      </div>

      <div className="max-w-2xl mx-auto px-4 space-y-3 pb-8">
        {isLoading && <p className="text-textMuted text-center py-8">Loading...</p>}
        {!isLoading && incidents.length === 0 && (
          <p className="text-textMuted text-center py-8">No incidents found.</p>
        )}

        {incidents.map((inc) => (
          <div key={inc.id} className="bg-white rounded-xl border border-border p-4">
            <div className="flex items-center gap-2 mb-2">
              <SeverityBadge severity={inc.severity} />
              <span className="font-medium text-textPrimary text-sm">{inc.incident_type}</span>
              <StatusBadge status={inc.status} />
              <span className="text-textMuted text-xs ml-auto">
                {formatDistanceToNow(new Date(inc.created_at), { addSuffix: true })}
              </span>
            </div>
            <p className="text-textBody text-sm line-clamp-2 mb-2">{inc.description}</p>
            <div className="flex items-center gap-3 text-xs text-textMuted">
              {inc.zone_name && <span>📍 {inc.zone_name}</span>}
              <span>👍 {inc.vouch_count}</span>
              {inc.donation_count > 0 && <span>₦{inc.total_donations_naira?.toLocaleString()}</span>}
            </div>
            <div className="flex gap-2 mt-3">
              <Link to={`/track/${inc.id}`} className="text-primary text-xs font-semibold hover:underline">View details →</Link>
              <button
                onClick={() => vouchMut.mutate(inc.id)}
                className="text-xs text-textMuted hover:text-primary"
              >
                Vouch
              </button>
              <button
                onClick={() => navigator.clipboard.writeText(`${window.location.origin}/track/${inc.id}`)}
                className="text-xs text-textMuted hover:text-primary"
              >
                Share
              </button>
            </div>
          </div>
        ))}

        {/* Pagination */}
        <div className="flex gap-3 justify-center pt-4">
          {page > 1 && (
            <button onClick={() => setPage((p) => p - 1)} className="border border-border px-4 py-2 rounded-lg text-sm hover:border-primary">
              Previous
            </button>
          )}
          {hasNext && (
            <button onClick={() => setPage((p) => p + 1)} className="border border-border px-4 py-2 rounded-lg text-sm hover:border-primary">
              Load more
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
