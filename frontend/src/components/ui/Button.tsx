import { Link } from 'react-router-dom'
import clsx from 'clsx'
import type { ReactNode, ButtonHTMLAttributes } from 'react'

/**
 * Single button system. Replaces ad-hoc per-page classes (which had navy
 * backgrounds with red hover states — two colour systems fighting).
 *
 * `danger` exists for genuinely destructive/critical actions only. Red is not
 * available as a decorative variant anywhere in the product.
 */
type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'inverse'
type Size = 'sm' | 'md' | 'lg'

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-primary-700 text-ink-invert hover:bg-primary-800 active:bg-primary-900 shadow-xs',
  secondary:
    'bg-surface text-ink border border-line-strong hover:bg-sunken active:bg-line',
  ghost:
    'text-primary-700 hover:bg-primary-50 active:bg-primary-100',
  danger:
    'bg-critical text-ink-invert hover:brightness-95 active:brightness-90 shadow-xs',
  inverse:
    'bg-surface text-primary-700 hover:bg-primary-50 active:bg-primary-100 shadow-sm',
}

const SIZES: Record<Size, string> = {
  sm: 'h-9 px-3 text-caption gap-1.5',
  md: 'h-11 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-body gap-2',
}

/** Minimum 44px touch target on md/lg per WCAG 2.2 target-size guidance. */
const BASE =
  'inline-flex items-center justify-center rounded-md font-semibold transition-colors duration-fast ' +
  'disabled:opacity-50 disabled:pointer-events-none select-none whitespace-nowrap'

interface CommonProps {
  variant?: Variant
  size?: Size
  fullWidth?: boolean
  className?: string
  children: ReactNode
}

export function Button({
  variant = 'primary',
  size = 'md',
  fullWidth,
  className,
  children,
  ...rest
}: CommonProps & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={clsx(BASE, VARIANTS[variant], SIZES[size], fullWidth && 'w-full', className)}
      {...rest}
    >
      {children}
    </button>
  )
}

export function ButtonLink({
  to,
  href,
  variant = 'primary',
  size = 'md',
  fullWidth,
  className,
  children,
  ...rest
}: CommonProps & {
  to?: string
  href?: string
} & React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const cls = clsx(BASE, VARIANTS[variant], SIZES[size], fullWidth && 'w-full', className)

  if (to) {
    return (
      <Link to={to} className={cls}>
        {children}
      </Link>
    )
  }
  return (
    <a className={cls} href={href} {...rest}>
      {children}
    </a>
  )
}
