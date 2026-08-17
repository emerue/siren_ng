import { Check, Circle, Inbox, ScanLine, ShieldCheck, Users, Landmark, Flag } from 'lucide-react'
import clsx from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import type { LucideIcon } from 'lucide-react'

/**
 * The incident lifecycle, told in plain language.
 *
 * This is the product's most important trust surface: it shows exactly what
 * Siren has done and — just as importantly — what it has NOT done yet.
 *
 * Promise invariant (§8): every stage describes a Siren action. No stage
 * promises that emergency services will arrive.
 */

interface ResponseLog {
  id: number | string
  to_status: string
  note?: string
  actor?: string
  created_at: string
}

interface Stage {
  key: string
  label: string
  description: string
  icon: LucideIcon
  /** Backend statuses that mean this stage has completed. */
  completedBy: string[]
}

const STAGES: Stage[] = [
  {
    key: 'received',
    label: 'Report received',
    description: 'Siren received the report on WhatsApp and acknowledged the reporter.',
    icon: Inbox,
    completedBy: ['DETECTED', 'VERIFYING', 'VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED', 'REJECTED', 'CLOSED'],
  },
  {
    key: 'sorted',
    label: 'Sorted automatically',
    description: 'Type, severity and area were classified to help the coordinator review it quickly.',
    icon: ScanLine,
    completedBy: ['DETECTED', 'VERIFYING', 'VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED', 'REJECTED', 'CLOSED'],
  },
  {
    key: 'verified',
    label: 'Confirmed by a Siren coordinator',
    description: 'A person reviews every report. Nothing is sent to neighbours until they confirm it.',
    icon: ShieldCheck,
    completedBy: ['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED'],
  },
  {
    key: 'alerted',
    label: 'Neighbours alerted',
    description: 'Subscribers in this LGA were sent a WhatsApp alert.',
    icon: Users,
    completedBy: ['RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED'],
  },
  {
    key: 'notified',
    label: 'Emergency services notified',
    description: 'Siren forwarded the confirmed report to official channels. Siren cannot guarantee their response.',
    icon: Landmark,
    completedBy: ['AGENCY_NOTIFIED', 'RESOLVED'],
  },
  {
    key: 'resolved',
    label: 'Resolved',
    description: 'The incident was closed and the reporter was told.',
    icon: Flag,
    completedBy: ['RESOLVED'],
  },
]

function stageTimestamp(stage: Stage, logs: ResponseLog[]): string | null {
  const match = logs.find((l) => stage.completedBy.includes(l.to_status))
  return match?.created_at ?? null
}

export default function IncidentTimeline({
  status,
  logs = [],
  createdAt,
}: {
  status: string
  logs?: ResponseLog[]
  createdAt?: string
}) {
  const rejected = status === 'REJECTED'
  const ordered = [...logs].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  )

  // A rejected report stops after review — showing later stages would imply
  // actions that never happened.
  const visible = rejected ? STAGES.slice(0, 2) : STAGES

  const firstIncompleteIndex = visible.findIndex((s) => !s.completedBy.includes(status))

  return (
    <div>
      <ol className="relative space-y-0" role="list">
        {visible.map((stage, i) => {
          const done = stage.completedBy.includes(status)
          const current = i === firstIncompleteIndex
          const Icon = stage.icon
          const ts = stage.key === 'received' ? createdAt ?? null : stageTimestamp(stage, ordered)
          const isLast = i === visible.length - 1

          return (
            <li key={stage.key} className="relative flex gap-3.5 pb-6 last:pb-0">
              {/* Connector */}
              {!isLast && (
                <span
                  aria-hidden="true"
                  className={clsx(
                    'absolute left-[15px] top-8 h-[calc(100%-1rem)] w-px',
                    done ? 'bg-primary-200' : 'bg-line',
                  )}
                />
              )}

              {/* Marker — icon carries meaning alongside colour */}
              <span
                className={clsx(
                  'relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-4 ring-surface',
                  done && 'bg-primary-700 text-ink-invert',
                  !done && current && 'bg-accent-50 text-status-detected ring-4',
                  !done && !current && 'bg-sunken text-ink-faint',
                )}
              >
                {done ? (
                  <Check className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Icon className="h-4 w-4" aria-hidden="true" />
                )}
              </span>

              <div className="min-w-0 flex-1 pt-0.5">
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  <h3
                    className={clsx(
                      'text-sm font-semibold',
                      done ? 'text-ink' : current ? 'text-status-detected' : 'text-ink-muted',
                    )}
                  >
                    {stage.label}
                  </h3>
                  {/* Screen-reader status, so state is never colour-only */}
                  <span className="sr-only">
                    {done ? '— completed' : current ? '— in progress' : '— not yet'}
                  </span>
                  {ts && done && (
                    <time dateTime={ts} className="text-caption text-ink-faint">
                      {formatDistanceToNow(new Date(ts), { addSuffix: true })}
                    </time>
                  )}
                  {current && !done && (
                    <span className="text-caption font-medium text-status-detected">In progress</span>
                  )}
                </div>
                <p className="mt-0.5 text-caption text-ink-muted">{stage.description}</p>
              </div>
            </li>
          )
        })}
      </ol>

      {rejected && (
        <div className="mt-2 flex gap-2.5 rounded-md bg-sunken px-3.5 py-3">
          <Circle className="mt-0.5 h-4 w-4 shrink-0 text-ink-muted" aria-hidden="true" />
          <p className="text-caption text-ink-body">
            A coordinator reviewed this report and did not confirm it as an emergency.
            No alert was sent to neighbours.
          </p>
        </div>
      )}
    </div>
  )
}
