import { useState, useCallback } from 'react'
import Nav from '../components/Nav'
import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { getIncidents, vouchIncident, getHistoricalIncidents } from '../api'
import type { Incident } from '../types'
import HistoricalIncidentCard, { HistoricalSectionDivider } from '../components/HistoricalIncidentCard'

function SeverityBadge({ severity }: { severity: string }) {
  const c: Record<string, string> = {
    CRITICAL: 'bg-red-600 text-white', HIGH: 'bg-red-500 text-white',
    MEDIUM: 'bg-amber-500 text-white', LOW: 'bg-yellow-200 text-gray-800',
  }
  return <span className={`text-xs font-bold px-2 py-0.5 rounded ${c[severity] || 'bg-gray-200 text-gray-600'}`}>{severity}</span>
}

function StatusBadge({ status }: { status: string }) {
  const c: Record<string, string> = {
    VERIFIED: 'bg-blue-100 text-blue-800', RESPONDING: 'bg-green-100 text-green-800',
    VERIFYING: 'bg-yellow-100 text-amber-700', RESOLVED: 'bg-green-100 text-green-800',
    AGENCY_NOTIFIED: 'bg-purple-100 text-purple-800',
  }
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${c[status] || 'bg-gray-100 text-gray-500'}`}>{status.replace('_', ' ')}</span>
}

export default function FeedPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ zone_name: '', incident_type: '', severity: '', status: '' })
  const [showHistorical, setShowHistorical] = useState(false)
  const [histPage, setHistPage] = useState(1)
  const [yearFrom, setYearFrom] = useState(2010)
  const [yearTo, setYearTo] = useState(new Date().getFullYear())

  const liveParams = Object.fromEntries(
    Object.entries({
      ...filters,
      page: String(page),
      historical: 'false',  // exclude old resolved from live feed
    }).filter(([, v]) => v && v !== 'false')
  )
  // Re-add historical=false explicitly
  liveParams.historical = 'false'

  const { data, isLoading } = useQuery({
    queryKey: ['incidents', liveParams],
    queryFn: () => getIncidents(liveParams),
  })

  const histParams: Record<string, string> = {
    page: String(histPage),
    page_size: '20',
  }
  if (filters.zone_name) histParams.zone_name = filters.zone_name
  if (filters.incident_type) histParams.incident_type = filters.incident_type
  if (filters.severity) histParams.severity = filters.severity
  if (yearFrom > 2010) histParams.year_from = String(yearFrom)
  if (yearTo < new Date().getFullYear()) histParams.year_to = String(yearTo)

  const { data: histData, isLoading: histLoading } = useQuery({
    queryKey: ['historical-incidents', histParams],
    queryFn: () => getHistoricalIncidents(histParams),
    enabled: showHistorical,
  })

  const incidents: Incident[] = data?.results || []
  const hasNext = !!data?.next
  const historical: Incident[] = histData?.results || []
  const histHasNext = !!histData?.next

  const qc = useQueryClient()
  const vouchMut = useMutation({
    mutationFn: (id: string) => vouchIncident(id, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['incidents'] }),
  })

  function updateFilter(key: string, value: string) {
    setFilters((f) => ({ ...f, [key]: value }))
    setPage(1)
    setHistPage(1)
  }

  return (
    <div className="min-h-screen bg-bg font-sans">
      <Nav />

      {/* Filter bar */}
      <div className="max-w-2xl mx-auto px-4 py-4 flex flex-wrap gap-2 items-center">
        {[
          { key: 'incident_type', options: ['', 'FIRE', 'FLOOD', 'COLLAPSE', 'RTA', 'EXPLOSION', 'DROWNING', 'HAZARD'], label: 'Type' },
          { key: 'severity', options: ['', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'], label: 'Severity' },
          { key: 'status', options: ['', 'VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED'], label: 'Status' },
        ].map(({ key, options, label }) => (
          <select
            key={key}
            value={filters[key as keyof typeof filters]}
            onChange={(e) => updateFilter(key, e.target.value)}
            className="border border-border rounded-lg px-3 py-1.5 text-sm text-textBody"
          >
            <option value="">{label}: All</option>
            {options.slice(1).map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        ))}
        <input
          placeholder="Zone"
          value={filters.zone_name}
          onChange={(e) => updateFilter('zone_name', e.target.value)}
          className="border border-border rounded-lg px-3 py-1.5 text-sm w-28"
        />

        {/* Historical toggle pill */}
        <button
          onClick={() => setShowHistorical((v) => !v)}
          className={`ml-auto px-4 py-1.5 rounded-full text-xs font-semibold border transition-all ${
            showHistorical
              ? 'bg-teal-600 text-white border-teal-600'
              : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
          }`}
        >
          {showHistorical ? 'Including history' : 'Show history'}
        </button>
      </div>

      <div className="max-w-2xl mx-auto px-4 space-y-3 pb-8">
        {/* Live incidents */}
        {isLoading && <p className="text-textMuted text-center py-8">Loading...</p>}
        {!isLoading && incidents.length === 0 && !showHistorical && (
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
              <button onClick={() => vouchMut.mutate(inc.id)} className="text-xs text-textMuted hover:text-primary">Vouch</button>
              <button onClick={() => navigator.clipboard.writeText(`${window.location.origin}/track/${inc.id}`)} className="text-xs text-textMuted hover:text-primary">Share</button>
            </div>
          </div>
        ))}

        {/* Live pagination */}
        <div className="flex gap-3 justify-center pt-2">
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

        {/* Historical section (STATE 4 — RESEARCH) */}
        {showHistorical && (
          <>
            <HistoricalSectionDivider />

            {/* Year range filter */}
            <div className="flex items-center gap-3 pb-1">
              <span className="text-xs text-gray-500">Year range:</span>
              <select
                value={yearFrom}
                onChange={(e) => { setYearFrom(Number(e.target.value)); setHistPage(1) }}
                className="border border-border rounded px-2 py-1 text-xs"
              >
                {Array.from({ length: 16 }, (_, i) => 2010 + i).map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
              <span className="text-xs text-gray-400">to</span>
              <select
                value={yearTo}
                onChange={(e) => { setYearTo(Number(e.target.value)); setHistPage(1) }}
                className="border border-border rounded px-2 py-1 text-xs"
              >
                {Array.from({ length: 16 }, (_, i) => 2010 + i).map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>

            {histLoading && <p className="text-gray-400 text-center text-sm py-6">Loading historical records...</p>}

            {!histLoading && historical.length === 0 && (
              <div className="text-center py-8 px-4">
                <p className="text-gray-500 text-sm">No historical incidents match these filters for this zone.</p>
                <p className="text-gray-400 text-xs mt-1">Try expanding your date range or removing a filter.</p>
              </div>
            )}

            {historical.map((inc) => (
              <HistoricalIncidentCard key={inc.id} incident={inc} />
            ))}

            {/* Historical pagination */}
            <div className="flex gap-3 justify-center pt-2">
              {histPage > 1 && (
                <button onClick={() => setHistPage((p) => p - 1)} className="border border-border px-4 py-2 rounded-lg text-sm hover:border-gray-400">
                  Previous
                </button>
              )}
              {histHasNext && (
                <button onClick={() => setHistPage((p) => p + 1)} className="border border-gray-300 px-4 py-2 rounded-lg text-sm text-gray-600 hover:border-gray-400">
                  Load more historical records
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
