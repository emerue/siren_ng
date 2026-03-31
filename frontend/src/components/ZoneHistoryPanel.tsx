/**
 * ZoneHistoryPanel
 * Slide-up drawer. Tells the story of a zone through data visualisation.
 * NOT a list — an evidence-of-reliability narrative.
 * Emotional job: Satisfy curiosity without triggering anxiety.
 */
import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, XAxis, ResponsiveContainer, Tooltip,
} from 'recharts'
import { getZoneHistory } from '../api'
import type { ZoneHistory, Incident } from '../types'
import { format, parseISO } from 'date-fns'

const TYPE_ICON: Record<string, string> = {
  FIRE: '🔥', FLOOD: '🌊', COLLAPSE: '🏚', RTA: '🚗',
  EXPLOSION: '💥', DROWNING: '🆘', HAZARD: '⚡',
}

const SEV_COLOR: Record<string, string> = {
  CRITICAL: 'bg-red-500', HIGH: 'bg-orange-400',
  MEDIUM: 'bg-amber-400', LOW: 'bg-yellow-300',
}

interface Props {
  zoneName?: string
  lat?: number
  lng?: number
  radiusKm?: number
  locationLabel: string
  isOpen: boolean
  onClose: () => void
}

function TimelineRow({ inc }: { inc: Incident }) {
  const date = parseISO(inc.created_at)
  const month = format(date, 'MMM yyyy')
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-gray-100 last:border-0">
      <span className="text-base shrink-0">{TYPE_ICON[inc.incident_type] || '🚨'}</span>
      <div className="flex-1 min-w-0">
        <span className="text-sm text-gray-700 font-medium">{inc.incident_type}</span>
        <span className="text-xs text-gray-400 ml-2">{inc.zone_name} · {month}</span>
      </div>
      <span className={`w-2 h-2 rounded-full shrink-0 ${SEV_COLOR[inc.severity] || 'bg-gray-300'}`} />
      <span className="text-xs text-teal-600 font-medium shrink-0">✓ Resolved</span>
    </div>
  )
}

function EmptyZone({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-3 py-12 px-6 text-center">
      <div className="w-12 h-12 rounded-full bg-teal-50 flex items-center justify-center text-2xl">✓</div>
      <p className="text-gray-700 font-medium text-sm leading-relaxed">
        No documented incidents near {label} since 2010.
      </p>
      <p className="text-gray-400 text-xs">This is a good sign — we'll keep watching.</p>
    </div>
  )
}

export default function ZoneHistoryPanel({ zoneName, lat, lng, radiusKm, locationLabel, isOpen, onClose }: Props) {
  const overlayRef = useRef<HTMLDivElement>(null)

  const hasCoords = lat != null && lng != null
  const { data, isLoading } = useQuery<ZoneHistory>({
    queryKey: ['zone-history', lat ?? zoneName, lng],
    queryFn: () => getZoneHistory(hasCoords ? { lat, lng, radiusKm: radiusKm ?? 3 } : { zoneName: zoneName ?? '' }),
    enabled: isOpen && (hasCoords || !!zoneName),
    staleTime: 5 * 60 * 1000,
  })

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) document.body.style.overflow = 'hidden'
    else document.body.style.overflow = ''
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  if (!isOpen) return null

  const top3Types = data
    ? Object.entries(data.by_type).slice(0, 3)
    : []

  return (
    <>
      {/* Backdrop */}
      <div
        ref={overlayRef}
        className="fixed inset-0 bg-black/40 z-40"
        style={{ animation: 'fadeIn 200ms ease-out' }}
        onClick={onClose}
        aria-hidden
      />

      {/* Drawer */}
      <div
        className="fixed bottom-0 left-0 right-0 z-50 bg-white rounded-t-2xl shadow-2xl max-h-[88vh] overflow-y-auto"
        style={{ animation: 'slideUp 350ms cubic-bezier(0.4, 0, 0.2, 1)' }}
        role="dialog"
        aria-label={`${locationLabel} zone history`}
      >
        {/* Handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full bg-gray-300" />
        </div>

        <div className="px-5 pb-8">
          {/* Header */}
          <div className="flex items-center justify-between py-3 mb-2">
            <h2 className="font-bold text-gray-900 text-base">{locationLabel}</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 text-lg leading-none p-1"
              aria-label="Close"
            >
              ×
            </button>
          </div>

          {isLoading && (
            <div className="py-12 text-center text-gray-400 text-sm">Loading area history...</div>
          )}

          {data && data.total_incidents === 0 && (
            <EmptyZone label={locationLabel} />
          )}

          {data && data.total_incidents > 0 && (
            <div className="space-y-6">

              {/* Section A: Headline stat */}
              <div>
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-4xl font-bold text-gray-900">{data.total_incidents}</span>
                  <span className="text-gray-400 text-sm">incidents were documented in this area</span>
                </div>
                <p className="text-xs text-gray-400 mb-3">across this zone · since 2010</p>

                {/* Type chips */}
                <div className="flex flex-wrap gap-2">
                  {top3Types.map(([type, count]) => (
                    <span
                      key={type}
                      className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1 bg-gray-100 text-gray-700 rounded-full"
                    >
                      {TYPE_ICON[type] || '🚨'} {count} {type.toLowerCase()}{count !== 1 ? 's' : ''}
                    </span>
                  ))}
                </div>
              </div>

              {/* Section B: Trend chart */}
              {data.by_year.length > 1 && (
                <div>
                  <p className="text-xs text-gray-500 font-medium mb-3 uppercase tracking-wide">
                    Incident frequency over time
                  </p>
                  <div style={{ height: 100 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart
                        data={data.by_year}
                        margin={{ top: 4, right: 4, left: 0, bottom: 0 }}
                      >
                        <XAxis
                          dataKey="year"
                          tick={{ fontSize: 10, fill: '#9CA3AF' }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          contentStyle={{
                            fontSize: 11, border: '1px solid #E5E7EB',
                            borderRadius: 8, background: 'white', padding: '4px 8px',
                          }}
                          formatter={(v: number) => [`${v} incidents`, '']}
                          labelFormatter={(y: number) => String(y)}
                        />
                        <Area
                          type="monotone"
                          dataKey="count"
                          stroke="#0D9488"
                          strokeWidth={2}
                          fill="#0D9488"
                          fillOpacity={0.12}
                          dot={false}
                          animationDuration={800}
                          animationEasing="ease-out"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Section C: Resolution rate */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <p className="text-sm text-gray-700">
                    <span className="font-semibold text-green-700">{data.resolution_rate}%</span>
                    {' '}of incidents in this area were resolved
                  </p>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all duration-700"
                    style={{ width: `${data.resolution_rate}%` }}
                  />
                </div>
                {data.avg_resolution_minutes !== null && (
                  <p className="text-xs text-gray-400 mt-1.5">
                    Average resolution time: {data.avg_resolution_minutes} minutes
                  </p>
                )}
                {data.avg_resolution_minutes === null && (
                  <p className="text-xs text-gray-400 mt-1.5">
                    Siren coordinated the community response in each case
                  </p>
                )}
              </div>

              {/* Section D: Recent 5 timeline */}
              {data.recent_5.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 font-medium mb-2 uppercase tracking-wide">
                    Recently documented
                  </p>
                  <div>
                    {data.recent_5.map((inc) => (
                      <TimelineRow key={inc.id} inc={inc} />
                    ))}
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); }
          to   { transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>
    </>
  )
}
