import { Link, useLocation } from 'react-router-dom'
import { useEffect, useRef, useState } from 'react'
import { Menu, X, Siren as SirenIcon } from 'lucide-react'
import clsx from 'clsx'
import { useAuthStore } from '../store/authStore'
import { useFeatures } from '../hooks/useFeatures'
import { ButtonLink } from './ui/Button'
import { waLink } from '../lib/whatsapp'

/**
 * Primary navigation.
 *
 * IA principle (§16): navigation contains destinations that serve the web
 * layer's real job — explain, build trust, let people check what Siren did.
 * Pages for HIDDEN/OUT features are not surfaced; add `feature` to gate a link
 * behind a flag from GET /api/features/.
 */
const NAV_LINKS: { to: string; label: string; feature?: string }[] = [
  { to: '/#how-it-works', label: 'How it works' },
  { to: '/feed', label: 'Live incidents' },
  { to: '/connect', label: 'Get alerts' },
  { to: '/guardian', label: 'Guardian', feature: 'guardian_web' },
]

export default function Nav() {
  const location = useLocation()
  const token = useAuthStore((s) => s.token)
  const [open, setOpen] = useState(false)
  const { isOn } = useFeatures()
  const panelRef = useRef<HTMLDivElement>(null)
  const toggleRef = useRef<HTMLButtonElement>(null)

  const navLinks = NAV_LINKS.filter((l) => !l.feature || isOn(l.feature))

  // Close the drawer on route change so it never persists across navigation.
  useEffect(() => setOpen(false), [location.pathname])

  // Escape closes the drawer and returns focus to the toggle (keyboard a11y).
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false)
        toggleRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  const isActive = (path: string) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur supports-[backdrop-filter]:bg-surface/80">
      <a href="#main" className="skip-link">Skip to content</a>

      <nav aria-label="Main" className="mx-auto flex h-16 max-w-content items-center justify-between gap-4 px-5 sm:px-6">
        <Link
          to="/"
          className="flex items-center gap-2 font-bold tracking-tight text-ink"
          aria-label="Siren.ng — home"
        >
          <SirenIcon className="h-5 w-5 text-primary-700" aria-hidden="true" />
          <span className="text-[1.0625rem]">Siren<span className="text-ink-muted">.ng</span></span>
        </Link>

        {/* Desktop */}
        <div className="hidden items-center gap-1 md:flex">
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              aria-current={isActive(to) ? 'page' : undefined}
              className={clsx(
                'rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast',
                isActive(to)
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-ink-body hover:bg-sunken hover:text-ink',
              )}
            >
              {label}
            </Link>
          ))}
          {token && (
            <Link
              to="/dashboard"
              className="rounded-md px-3 py-2 text-sm font-medium text-ink-muted transition-colors duration-fast hover:bg-sunken hover:text-ink"
            >
              Dashboard
            </Link>
          )}
          <ButtonLink
            href={waLink('I want to report an emergency')}
            target="_blank"
            rel="noopener noreferrer"
            size="sm"
            className="ml-2"
          >
            Report on WhatsApp
          </ButtonLink>
        </div>

        {/* Mobile */}
        <div className="flex items-center gap-2 md:hidden">
          <ButtonLink
            href={waLink('I want to report an emergency')}
            target="_blank"
            rel="noopener noreferrer"
            size="sm"
          >
            Report
          </ButtonLink>
          <button
            ref={toggleRef}
            onClick={() => setOpen((v) => !v)}
            className="flex h-11 w-11 items-center justify-center rounded-md text-ink-body transition-colors duration-fast hover:bg-sunken"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            aria-controls="mobile-menu"
          >
            {open ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </nav>

      {/* Mobile drawer */}
      {open && (
        <div
          id="mobile-menu"
          ref={panelRef}
          className="animate-fade-up border-t border-line bg-surface px-3 py-3 md:hidden"
        >
          {navLinks.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              aria-current={isActive(to) ? 'page' : undefined}
              className={clsx(
                'block rounded-md px-3 py-3 text-sm font-medium transition-colors duration-fast',
                isActive(to) ? 'bg-primary-50 text-primary-700' : 'text-ink-body hover:bg-sunken',
              )}
            >
              {label}
            </Link>
          ))}
          {token && (
            <Link
              to="/dashboard"
              className="block rounded-md px-3 py-3 text-sm font-medium text-ink-muted hover:bg-sunken"
            >
              Dashboard
            </Link>
          )}
        </div>
      )}
    </header>
  )
}
