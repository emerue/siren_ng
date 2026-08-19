import {
  Clock,
  ShieldCheck,
  Users,
  Landmark,
  CheckCircle2,
  XCircle,
  Archive,
  type LucideIcon,
} from 'lucide-react'
import clsx from 'clsx'

/**
 * The single source of truth for how incident status is spoken and shown.
 *
 * Two rules from the BRD govern every string here:
 *  1. Promise invariant (§8) — we state what SIREN DID (alerted, notified).
 *     We never state or imply what a third party WILL do.
 *  2. Human-front verification (§5.1.2) — verification is credited to a named
 *     human coordinator, never to "AI".
 *
 * Accessibility: status is never colour-alone. Every pill renders colour +
 * icon + text label together (WCAG 1.4.1).
 */

export type IncidentStatus =
  | 'DETECTED'
  | 'VERIFYING'
  | 'VERIFIED'
  | 'RESPONDING'
  | 'AGENCY_NOTIFIED'
  | 'RESOLVED'
  | 'REJECTED'
  | 'CLOSED'

interface StatusMeta {
  label: string
  /** Plain-language explanation for a Lagos resident — no system jargon. */
  description: string
  icon: LucideIcon
  className: string
  dot: string
}

export const STATUS_META: Record<IncidentStatus, StatusMeta> = {
  DETECTED: {
    label: 'Awaiting coordinator',
    description: 'Received and sorted. A Siren coordinator has not confirmed it yet, so no alert has been sent.',
    icon: Clock,
    className: 'bg-accent-50 text-status-detected ring-accent-100',
    dot: 'bg-status-detected',
  },
  VERIFYING: {
    label: 'Awaiting coordinator',
    description: 'A Siren coordinator is reviewing this report. Nothing is broadcast until a person confirms it.',
    icon: Clock,
    className: 'bg-accent-50 text-status-detected ring-accent-100',
    dot: 'bg-status-detected',
  },
  VERIFIED: {
    label: 'Confirmed by coordinator',
    description: 'A Siren coordinator confirmed this report is a real emergency.',
    icon: ShieldCheck,
    className: 'bg-primary-50 text-status-verified ring-primary-100',
    dot: 'bg-status-verified',
  },
  RESPONDING: {
    label: 'Neighbours alerted',
    description: 'Subscribers in this LGA have been sent an alert.',
    icon: Users,
    className: 'bg-teal-50 text-status-alerted ring-teal-100',
    dot: 'bg-status-alerted',
  },
  AGENCY_NOTIFIED: {
    label: 'Emergency services notified',
    description: 'Siren sent this report to official emergency channels. Siren cannot guarantee their response.',
    icon: Landmark,
    className: 'bg-violet-50 text-status-notified ring-violet-100',
    dot: 'bg-status-notified',
  },
  RESOLVED: {
    label: 'Resolved',
    description: 'This incident has been closed.',
    icon: CheckCircle2,
    className: 'bg-green-50 text-status-resolved ring-green-100',
    dot: 'bg-status-resolved',
  },
  REJECTED: {
    label: 'Not verified',
    description: 'This report was not confirmed as an emergency. No alert was sent.',
    icon: XCircle,
    className: 'bg-sunken text-ink-muted ring-line',
    dot: 'bg-status-rejected',
  },
  CLOSED: {
    label: 'Closed',
    description: 'This incident is closed.',
    icon: Archive,
    className: 'bg-sunken text-ink-muted ring-line',
    dot: 'bg-status-rejected',
  },
}

export function statusMeta(status: string): StatusMeta {
  return STATUS_META[status as IncidentStatus] ?? STATUS_META.DETECTED
}

export function StatusPill({
  status,
  size = 'md',
  showIcon = true,
  className,
}: {
  status: string
  size?: 'sm' | 'md'
  showIcon?: boolean
  className?: string
}) {
  const meta = statusMeta(status)
  const Icon = meta.icon
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-md font-semibold ring-1 ring-inset',
        size === 'sm' ? 'px-2 py-0.5 text-overline uppercase' : 'px-2.5 py-1 text-caption',
        meta.className,
        className,
      )}
    >
      {showIcon && <Icon className={size === 'sm' ? 'h-3 w-3' : 'h-3.5 w-3.5'} aria-hidden="true" />}
      {meta.label}
    </span>
  )
}

/**
 * Severity describes the incident itself — never the UI's excitement level.
 * Only CRITICAL earns red.
 */
const SEVERITY_META: Record<string, { label: string; className: string }> = {
  LOW:      { label: 'Low',      className: 'bg-sunken text-ink-body ring-line' },
  MEDIUM:   { label: 'Medium',   className: 'bg-accent-50 text-severity-medium ring-accent-100' },
  HIGH:     { label: 'High',     className: 'bg-orange-50 text-severity-high ring-orange-100' },
  CRITICAL: { label: 'Critical', className: 'bg-red-50 text-severity-critical ring-red-200' },
}

export function SeverityTag({ severity, className }: { severity: string; className?: string }) {
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.LOW
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-sm px-1.5 py-0.5 text-overline uppercase ring-1 ring-inset',
        meta.className,
        className,
      )}
    >
      <span className="sr-only">Severity: </span>
      {meta.label}
    </span>
  )
}
