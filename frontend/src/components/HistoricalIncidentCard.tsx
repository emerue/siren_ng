/**
 * HistoricalIncidentCard
 * Visual differentiation from live incidents — ghost grey border, historical badge.
 * Emotional job: Inform without alarming.
 * Rules: no vouch, no donate, no share, no status badge (only "Resolved").
 */
import { useState } from 'react'
import { format, parseISO } from 'date-fns'
import type { Incident } from '../types'

const TYPE_ICON: Record<string, string> = {
  FIRE: '🔥', FLOOD: '🌊', COLLAPSE: '🏚', RTA: '🚗',
  EXPLOSION: '💥', DROWNING: '🆘', HAZARD: '⚡',
}

const SEV_DOT: Record<string, string> = {
  CRITICAL: 'bg-red-500', HIGH: 'bg-orange-400',
  MEDIUM: 'bg-amber-400', LOW: 'bg-yellow-300',
}

interface Props {
  incident: Incident
}

export default function HistoricalIncidentCard({ incident: inc }: Props) {
  const [expanded, setExpanded] = useState(false)

  const year = parseISO(inc.created_at).getFullYear()
  const monthYear = format(parseISO(inc.created_at), 'MMMM yyyy')

  return (
    <div
      className="rounded-xl p-4 cursor-pointer"
      style={{
        background: '#F9FAFB',
        borderLeft: '3px solid #9CA3AF',
        border: '1px solid #E5E7EB',
        borderLeftWidth: '3px',
        borderLeftColor: '#9CA3AF',
        // Override the uniform border with left accent
        borderLeftStyle: 'solid',
        animation: 'fadeInCard 300ms ease-out',
      }}
      onClick={() => setExpanded((e) => !e)}
    >
      {/* Top row: type + HISTORICAL badge */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-base" style={{ opacity: 0.6 }}>{TYPE_ICON[inc.incident_type] || '🚨'}</span>
          <span className="text-xs text-gray-500 font-medium">{inc.incident_type}</span>
        </div>
        <span
          className="text-xs font-medium px-2 py-0.5 rounded"
          style={{ background: '#E5E7EB', color: '#374151', fontSize: 11, fontWeight: 500 }}
        >
          HISTORICAL · {year}
        </span>
      </div>

      {/* Middle: zone + date + description */}
      <h4 className="font-semibold text-gray-900 text-sm">{inc.zone_name || 'Lagos'}</h4>
      <p className="text-xs text-gray-400 mb-1.5">{monthYear}</p>
      <p className={`text-sm text-gray-600 leading-relaxed ${expanded ? '' : 'line-clamp-2'}`}>
        {inc.description}
      </p>

      {/* Bottom row: resolved + severity + source */}
      <div className="flex items-center gap-3 mt-3">
        <span className="text-xs text-green-700 font-medium">✓ Resolved</span>
        <span className={`w-1.5 h-1.5 rounded-full ${SEV_DOT[inc.severity] || 'bg-gray-300'}`} />
        <span className="text-xs text-gray-400">{inc.severity}</span>
        {inc.address_text && (
          <span className="text-xs text-gray-300 hidden sm:inline truncate max-w-32">
            {inc.address_text}
          </span>
        )}
      </div>
    </div>
  )
}

export function HistoricalSectionDivider() {
  return (
    <div className="flex items-center gap-3 py-4 my-2">
      <div className="flex-1 h-px bg-gray-200" />
      <span className="text-xs text-gray-400 font-medium whitespace-nowrap px-2">
        Historical records · Lagos 2010–2025
      </span>
      <div className="flex-1 h-px bg-gray-200" />
    </div>
  )
}
