import clsx from 'clsx'
import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

/** Constrained page shell — content never stretches edge to edge. */
export function Container({
  children,
  size = 'default',
  className,
}: {
  children: ReactNode
  size?: 'default' | 'prose'
  className?: string
}) {
  return (
    <div
      className={clsx(
        'mx-auto w-full px-5 sm:px-6',
        size === 'prose' ? 'max-w-prose' : 'max-w-content',
        className,
      )}
    >
      {children}
    </div>
  )
}

/** Consistent vertical rhythm. Sections are landmarks, not just divs. */
export function Section({
  children,
  className,
  tone = 'canvas',
  id,
  labelledBy,
}: {
  children: ReactNode
  className?: string
  tone?: 'canvas' | 'surface' | 'sunken'
  id?: string
  labelledBy?: string
}) {
  const tones = {
    canvas: '',
    surface: 'bg-surface border-y border-line',
    sunken: 'bg-sunken',
  }
  return (
    <section
      id={id}
      aria-labelledby={labelledBy}
      className={clsx('py-14 sm:py-section', tones[tone], className)}
    >
      {children}
    </section>
  )
}

/**
 * Section heading. An eyebrow gives scannability without shouting; the heading
 * carries the hierarchy. Eyebrow is aria-hidden so screen readers hear one
 * coherent heading rather than a fragment.
 */
export function SectionHeading({
  eyebrow,
  title,
  lede,
  id,
  align = 'left',
  className,
}: {
  eyebrow?: string
  title: string
  lede?: string
  id?: string
  align?: 'left' | 'center'
  className?: string
}) {
  return (
    <div
      className={clsx(
        'max-w-prose',
        align === 'center' && 'mx-auto text-center',
        className,
      )}
    >
      {eyebrow && (
        <p className="mb-2.5 text-overline uppercase text-primary-500" aria-hidden="true">
          {eyebrow}
        </p>
      )}
      <h2 id={id} className="text-h1 sm:text-display text-ink">
        {title}
      </h2>
      {lede && <p className="mt-3 text-body-lg text-ink-body">{lede}</p>}
    </div>
  )
}

/**
 * Card. Used only where grouping genuinely helps — never card-inside-card.
 * `interactive` adds affordance for clickable surfaces.
 */
export function Card({
  children,
  className,
  interactive,
  as: Tag = 'div',
}: {
  children: ReactNode
  className?: string
  interactive?: boolean
  as?: 'div' | 'article' | 'li'
}) {
  return (
    <Tag
      className={clsx(
        'rounded-lg border border-line bg-surface',
        interactive &&
          'transition-colors duration-fast hover:border-line-strong hover:bg-primary-50/30',
        className,
      )}
    >
      {children}
    </Tag>
  )
}

/** Content-shaped loading placeholder — never a bare spinner. */
export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx('skeleton', className)} aria-hidden="true" />
}

/**
 * Empty states answer: what is happening, why is it empty, what can I do.
 * "No data found" is never acceptable.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon
  title: string
  description: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div
      className={clsx(
        'flex flex-col items-center rounded-lg border border-dashed border-line bg-surface px-6 py-12 text-center',
        className,
      )}
    >
      {Icon && (
        <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-sunken text-ink-muted">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      )}
      <h3 className="text-h3 text-ink">{title}</h3>
      <p className="mt-1.5 max-w-sm text-sm text-ink-muted">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

/**
 * Error state. Calm, human, actionable — never a stack trace or raw
 * exception text.
 */
export function ErrorState({
  title = 'We could not load this',
  description = 'Something went wrong on our side. Please try again in a moment.',
  onRetry,
  className,
}: {
  title?: string
  description?: string
  onRetry?: () => void
  className?: string
}) {
  return (
    <div
      role="alert"
      className={clsx(
        'rounded-lg border border-line bg-surface px-6 py-10 text-center',
        className,
      )}
    >
      <h3 className="text-h3 text-ink">{title}</h3>
      <p className="mt-1.5 text-sm text-ink-muted">{description}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-5 rounded-md border border-line-strong px-4 py-2 text-sm font-semibold text-ink transition-colors duration-fast hover:bg-sunken"
        >
          Try again
        </button>
      )}
    </div>
  )
}
