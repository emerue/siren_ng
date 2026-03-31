/**
 * ZoneSafetyScoreCard
 * Circular SVG ring showing zone safety score for a saved location.
 * Tapping opens the Zone History Panel drawer.
 * Emotional job: Reassurance + credibility.
 */
import { useEffect, useState } from 'react'
import type { LocationSubscription } from '../types'

interface Props {
  sub: LocationSubscription
  zoneName?: string
  totalIncidents?: number
  trend?: 'improving' | 'stable' | 'increasing'
  onOpenHistory: () => void
}

function scoreColor(score: number) {
  if (score >= 85) return '#0D9488'  // Guardian Teal
  if (score >= 60) return '#D97706'  // Caution Amber
  return '#EA580C'                   // Warning Orange
}

function ScoreRing({ score, animate }: { score: number; animate: boolean }) {
  const r = 52
  const circ = 2 * Math.PI * r
  const color = scoreColor(score)
  // Start fully empty, animate to target on mount
  const offset = animate ? circ * (1 - score / 100) : circ

  return (
    <svg width="128" height="128" viewBox="0 0 128 128" aria-label={`Safety score ${score}`}>
      {/* Track ring */}
      <circle cx="64" cy="64" r={r} fill="none" stroke="#E5E7EB" strokeWidth="9" />
      {/* Progress ring */}
      <circle
        cx="64" cy="64" r={r}
        fill="none"
        stroke={color}
        strokeWidth="9"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{
          transform: 'rotate(-90deg)',
          transformOrigin: '64px 64px',
          transition: animate ? 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)' : 'none',
        }}
      />
      {/* Score number */}
      <text
        x="64" y="64"
        textAnchor="middle"
        dominantBaseline="central"
        fill={color}
        fontSize="30"
        fontWeight="700"
        fontFamily="Inter, system-ui, sans-serif"
      >
        {score}
      </text>
    </svg>
  )
}

export default function ZoneSafetyScoreCard({ sub, zoneName: _zoneName, totalIncidents, trend, onOpenHistory }: Props) {
  const score = sub.safety_score ?? 80
  const [animate, setAnimate] = useState(false)
  const color = scoreColor(score)

  // Trigger ring animation shortly after mount
  useEffect(() => {
    const t = setTimeout(() => setAnimate(true), 120)
    return () => clearTimeout(t)
  }, [])

  const trendText = trend === 'improving'
    ? { label: 'Safer than last year', arrow: '↓', cls: 'text-teal-600' }
    : trend === 'increasing'
    ? { label: 'More active than last year', arrow: '↑', cls: 'text-amber-600' }
    : { label: 'Activity stable', arrow: '→', cls: 'text-gray-500' }

  return (
    <button
      onClick={onOpenHistory}
      className="w-full bg-white border border-gray-200 rounded-2xl p-5 flex flex-col items-center gap-2 hover:border-gray-300 hover:shadow-sm transition-all duration-200 text-center"
      aria-label={`Open zone history for ${sub.label}`}
    >
      <ScoreRing score={score} animate={animate} />

      {/* Location name */}
      <h3 className="font-bold text-base text-gray-900 mt-1">{sub.label}</h3>

      {/* Historical anchor copy */}
      {totalIncidents !== undefined && (
        <p className="text-xs text-gray-500 leading-relaxed">
          Based on {totalIncidents} incidents near this location since 2010
        </p>
      )}
      {totalIncidents === undefined && (
        <p className="text-xs text-gray-500">Monitoring this area since 2010</p>
      )}

      {/* Trend */}
      {trend && (
        <p className={`text-xs font-medium flex items-center gap-1 ${trendText.cls}`}>
          <span>{trendText.arrow}</span>
          <span>{trendText.label}</span>
        </p>
      )}

      {/* Safety label */}
      <p className="text-xs mt-0.5" style={{ color }}>
        {score >= 85 ? 'This area has been well-monitored' :
         score >= 60 ? 'Moderate activity documented' :
         'High-activity area — closely monitored'}
      </p>

      <span className="text-xs text-gray-400 mt-1 flex items-center gap-1">
        View area history <span className="text-xs">›</span>
      </span>
    </button>
  )
}
