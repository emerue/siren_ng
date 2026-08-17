import { Link } from 'react-router-dom'
import { Siren as SirenIcon } from 'lucide-react'
import { waLink, WHATSAPP_DISPLAY } from '../lib/whatsapp'

/**
 * Footer. Minimal and honest — it restates the promise boundary (§8) rather
 * than padding the page with links. The admin entry point is deliberately not
 * advertised here.
 */
export default function Footer() {
  return (
    <footer className="border-t border-line bg-surface">
      <div className="mx-auto max-w-content px-5 py-12 sm:px-6">
        <div className="flex flex-col gap-10 md:flex-row md:justify-between">
          <div className="max-w-sm">
            <div className="flex items-center gap-2 font-bold tracking-tight text-ink">
              <SirenIcon className="h-5 w-5 text-primary-700" aria-hidden="true" />
              <span className="text-[1.0625rem]">Siren<span className="text-ink-muted">.ng</span></span>
            </div>
            <p className="mt-3 text-caption text-ink-muted">
              Community emergency coordination for Lagos, on the channel people already use.
            </p>
            <a
              href={waLink('Hello Siren')}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-4 inline-block text-caption font-semibold text-primary-700 hover:underline"
            >
              WhatsApp {WHATSAPP_DISPLAY}
            </a>
          </div>

          <nav aria-label="Footer" className="grid grid-cols-2 gap-x-10 gap-y-2 sm:gap-x-16">
            <div className="flex flex-col gap-2.5">
              <h2 className="text-overline uppercase text-ink-faint">Product</h2>
              <Link to="/#how-it-works" className="text-caption text-ink-body hover:text-primary-700">How it works</Link>
              <Link to="/feed" className="text-caption text-ink-body hover:text-primary-700">Live incidents</Link>
              <Link to="/connect" className="text-caption text-ink-body hover:text-primary-700">Get alerts</Link>
            </div>
            <div className="flex flex-col gap-2.5">
              <h2 className="text-overline uppercase text-ink-faint">Take part</h2>
              <Link to="/join" className="text-caption text-ink-body hover:text-primary-700">Volunteer</Link>
              <Link to="/organisations" className="text-caption text-ink-body hover:text-primary-700">Organisations</Link>
            </div>
          </nav>
        </div>

        {/* The promise boundary, stated plainly where anyone can find it. */}
        <div className="mt-10 border-t border-line pt-6">
          <p className="max-w-prose text-caption text-ink-muted">
            Siren alerts your neighbours and notifies emergency services. Siren is not an
            emergency service and cannot guarantee that anyone will arrive. In a
            life-threatening emergency, call <strong className="font-semibold text-ink-body">767</strong> or{' '}
            <strong className="font-semibold text-ink-body">112</strong>.
          </p>
          <p className="mt-4 text-caption text-ink-faint">
            © {new Date().getFullYear()} Siren.ng · Built for Lagos.
          </p>
        </div>
      </div>
    </footer>
  )
}
