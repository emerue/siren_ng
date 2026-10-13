import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ShieldCheck, CheckCircle2, Activity } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { getActiveIncidents } from '../api'
import type { Incident } from '../types'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import { ButtonLink } from '../components/ui/Button'
import { Container, Skeleton, EmptyState } from '../components/ui/Primitives'
import { StatusPill, SeverityTag } from '../components/ui/StatusPill'
import { useWhatsApp } from '../hooks/useWhatsApp'
import { incidentTypeLabel } from '../lib/incident'

/**
 * Landing page.
 *
 * The web layer is an explanation and trust surface, not the emergency
 * reporting app — reporting happens on WhatsApp (BRD §45).
 *
 * Design: the product lives inside a chat thread, and what separates it from
 * every other alert service is a human pause between a report arriving and
 * anything being broadcast. So the thread is the hero at real scale, and the
 * coordinator's confirmation is the one emphatic moment on the page. One
 * incident runs through the whole page — the hero opens it at 11:04, the
 * sequence section follows the same report to 13:22.
 *
 * The hero and footer sit on night (Siren speaking); everything between them
 * is black on white (the public record). Teal marks human confirmation and
 * nothing else. Red stays reserved for genuine criticality.
 *
 * Deliberately absent (BRD §5.2/§5.3): donations, resource boards, historical
 * data, zone safety scores, Guardian/Commute surfaces.
 */

/* ── Hero ──────────────────────────────────────────────────────────────── */

/**
 * The reveal. Five moments land in sequence on load so the pause between the
 * report and the confirmation is felt rather than described. This is the only
 * non-user-triggered motion on the page; `prefers-reduced-motion` drops it to
 * a static thread (see index.css).
 */
function Thread() {
  return (
    <div className="space-y-2.5" aria-hidden="true">
      <div className="thread-step" style={{ '--step': 0 } as React.CSSProperties}>
        <p className="mb-1.5 text-caption text-primary-200">A resident, 11:04</p>
        <div className="max-w-[90%] rounded-xl rounded-tl-sm bg-wash px-4 py-3">
          <p className="text-body text-ink">Fire for Isolo market, near the bus stop</p>
        </div>
      </div>

      <div className="thread-step" style={{ '--step': 1 } as React.CSSProperties}>
        <div className="ml-auto max-w-[90%] rounded-xl rounded-tr-sm bg-primary-600 px-4 py-3">
          <p className="text-body text-ink-invert">Received. A coordinator is checking it now.</p>
          <p className="mt-1 text-caption text-primary-200">11:04</p>
        </div>
      </div>

      {/* The pause. The product's whole claim, given its own space. */}
      <div
        className="thread-step flex items-center gap-3 py-3"
        style={{ '--step': 2 } as React.CSSProperties}
      >
        <span className="h-px flex-1 bg-primary-600" />
        <p className="text-caption text-primary-200">six minutes while a person reads it</p>
        <span className="h-px flex-1 bg-primary-600" />
      </div>

      <div className="thread-step" style={{ '--step': 3 } as React.CSSProperties}>
        <div className="flex items-start gap-3 rounded-xl border border-confirm/60 bg-confirm/10 px-4 py-3.5">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-confirm" aria-hidden="true" />
          <div>
            <p className="text-body font-semibold text-ink-invert">
              Confirmed by a Siren coordinator
            </p>
            <p className="mt-0.5 text-caption text-primary-200">11:10</p>
          </div>
        </div>
      </div>

      <div className="thread-step" style={{ '--step': 4 } as React.CSSProperties}>
        <p className="mb-1.5 text-caption text-primary-200">
          Sent to everyone watching Oshodi-Isolo, 11:10
        </p>
        <div className="rounded-xl rounded-tl-sm bg-surface px-4 py-3.5">
          <div className="flex items-center gap-2">
            <SeverityTag severity="HIGH" />
            <span className="text-caption font-semibold text-ink">Fire in Oshodi-Isolo</span>
          </div>
          <p className="mt-2 text-caption text-ink-body">
            Confirmed by a Siren coordinator. Your neighbours here have been alerted and
            emergency services notified.
          </p>
        </div>
      </div>
    </div>
  )
}

function Hero() {
  const { waLink } = useWhatsApp()

  return (
    <section className="bg-night">
      <Container className="py-14 sm:py-20">
        <div className="grid gap-12 lg:grid-cols-[1fr_27rem] lg:items-center lg:gap-20">
          <div>
            <h1 className="text-display font-extrabold text-ink-invert sm:text-display-lg">
              Someone reads your report before your street hears about it.
            </h1>

            <p className="mt-6 max-w-[54ch] text-body-lg text-primary-100">
              Send what you saw to Siren on WhatsApp. A coordinator confirms it is real,
              then everyone subscribed in your LGA is alerted and emergency services are
              notified. Nothing goes out until a person says so.
            </p>

            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <ButtonLink
                href={waLink('I want to report an emergency')}
                target="_blank"
                rel="noopener noreferrer"
                variant="inverse"
                size="lg"
              >
                Report an emergency
              </ButtonLink>
              <ButtonLink
                to="/connect"
                size="lg"
                className="border border-primary-400 bg-transparent text-ink-invert hover:bg-primary-600"
              >
                Get alerts for your area
              </ButtonLink>
            </div>

            <p className="mt-6 text-sm text-primary-200">
              Nothing to install, no account. Piloting in Oshodi-Isolo, Lagos.
            </p>
          </div>

          <Thread />
        </div>
      </Container>
    </section>
  )
}

/* ── Why it exists ─────────────────────────────────────────────────────── */

/**
 * The 78% figure as the subject of a sentence rather than a stat tile. The two
 * supporting figures sit in the source line, where they belong — they qualify
 * the first one instead of competing with it.
 */
function Why() {
  return (
    <section className="border-b border-line bg-surface py-14 sm:py-section">
      <Container>
        <div className="max-w-[62ch]">
          <p className="text-h2 font-normal text-ink-body">
            In a medical emergency,{' '}
            <strong className="text-display font-extrabold leading-none text-ink">
              78 in 100
            </strong>{' '}
            Lagosians call family, friends or a neighbour first. About three call an
            ambulance.
          </p>
          <p className="mt-6 max-w-[58ch] text-body-lg text-ink-body">
            That response is already happening on your street, and it is fast. What it
            lacks is any way to tell a real emergency from a rumour. Siren adds the
            missing step — a person who checks — and then carries the confirmed report
            to the neighbours who can act on it.
          </p>
          <p className="mt-6 text-caption text-ink-faint">
            Figures from an Emergency Response Africa survey. Roughly 95% of Nigerian
            internet users are reachable on WhatsApp, which is why Siren lives there and
            not in an app.
          </p>
        </div>
      </Container>
    </section>
  )
}

/* ── The sequence ──────────────────────────────────────────────────────── */

/**
 * The same incident the hero opened, followed to the end. A transcript down a
 * single rule rather than a rail of five cards: this is a sequence in time, and
 * the timeline is a real product surface (the public incident page), so the form
 * matches something the reader will actually meet later.
 */
const MOMENTS = [
  {
    time: '11:04',
    title: 'The report arrives',
    body: 'A resident sends what they saw, in English or Pidgin, however short. A photo helps but is not required. Siren replies straight away so they know it landed.',
  },
  {
    time: '11:04',
    title: 'Software sorts it, and stops',
    body: 'The report is classified automatically to put it in front of a coordinator faster. That is the limit of what software decides. It cannot alert anyone.',
  },
  {
    time: '11:10',
    title: 'A named coordinator confirms it',
    body: 'A person reads the report and decides whether it is real. This is the only action in the entire system that can send an alert to a neighbourhood.',
    pivot: true,
  },
  {
    time: '11:10',
    title: 'Neighbours are alerted',
    body: 'Everyone subscribed to that LGA gets a WhatsApp message saying what happened, where, and that a coordinator confirmed it.',
  },
  {
    time: '11:10',
    title: 'Emergency services are notified',
    body: 'Siren forwards every confirmed report to official channels and records that it was sent. We never tell you what they will do about it.',
  },
  {
    time: '13:22',
    title: 'The reporter is told it is over',
    body: 'When the incident closes, the person who reported it hears back. The record stays public at its own page, with a timestamp against every step.',
  },
]

function Sequence() {
  return (
    <section
      id="how-it-works"
      aria-labelledby="sequence-heading"
      className="border-b border-line bg-canvas py-14 sm:py-section"
    >
      <Container>
        <h2 id="sequence-heading" className="max-w-[48ch] text-h1 text-ink sm:text-display">
          One report, followed all the way through.
        </h2>
        <p className="mt-4 max-w-[58ch] text-body-lg text-ink-body">
          This is the incident from above, from the message arriving to the reporter
          hearing it is over. Every step is something Siren did, and every one of them
          is visible on the public page afterwards.
        </p>

        <ol className="mt-12 max-w-[64ch]">
          {MOMENTS.map((m) => (
            <li key={m.title + m.time} className="relative flex gap-5 pb-9 last:pb-0 sm:gap-7">
              {/* Rule and node. Last item stops the rule rather than trailing off. */}
              <div className="relative flex w-14 shrink-0 justify-end sm:w-16">
                <span
                  aria-hidden="true"
                  className="absolute right-[-1.375rem] top-2 h-full w-px bg-line-strong sm:right-[-1.875rem]"
                />
                <p
                  className={
                    m.pivot
                      ? 'relative z-10 font-command text-caption text-confirm'
                      : 'relative z-10 font-command text-caption text-ink-faint'
                  }
                >
                  {m.time}
                </p>
                <span
                  aria-hidden="true"
                  className={
                    m.pivot
                      ? 'absolute right-[-1.625rem] top-[0.3125rem] z-10 h-2.5 w-2.5 rounded-full bg-confirm ring-4 ring-canvas sm:right-[-2.125rem]'
                      : 'absolute right-[-1.5rem] top-[0.4375rem] z-10 h-1.5 w-1.5 rounded-full bg-line-strong ring-4 ring-canvas sm:right-[-2rem]'
                  }
                />
              </div>

              <div className="pt-px">
                <h3
                  className={
                    m.pivot
                      ? 'text-h3 font-bold text-confirm'
                      : 'text-h3 text-ink'
                  }
                >
                  {m.title}
                </h3>
                <p className="mt-1.5 max-w-[52ch] text-sm text-ink-body">{m.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </Container>
    </section>
  )
}

/* ── What Siren promises ───────────────────────────────────────────────── */

/**
 * The promise boundary (BRD §8). Stated as two plain columns, because the thing
 * that earns trust here is being specific about the limit, not decorating it.
 */
function PromiseBoundary() {
  return (
    <section
      aria-labelledby="promise-heading"
      className="border-b border-line bg-surface py-14 sm:py-section"
    >
      <Container>
        <h2 id="promise-heading" className="max-w-[46ch] text-h1 text-ink sm:text-display">
          What Siren promises, and what it cannot.
        </h2>
        <p className="mt-4 max-w-[58ch] text-body-lg text-ink-body">
          A false alarm spreads panic and costs us the only thing that makes this work.
          So speed never overrides the person checking, and we do not claim credit for
          anything we did not do.
        </p>

        <div className="mt-11 grid gap-x-12 gap-y-9 sm:grid-cols-2">
          <div>
            <h3 className="border-t-2 border-confirm pt-4 text-h3 text-ink">
              What we do
            </h3>
            <ul className="mt-4 space-y-3">
              {[
                'Confirm the report with a named coordinator before anyone is alerted.',
                'Alert everyone subscribed in that LGA, saying who confirmed it and when.',
                'Forward the confirmed report to emergency services, and record that we sent it.',
                'Tell the person who reported it when the incident closes.',
                'Keep your phone number out of every alert and off the site.',
              ].map((line) => (
                <li key={line} className="flex gap-2.5">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0 text-confirm"
                    aria-hidden="true"
                  />
                  <p className="text-sm text-ink-body">{line}</p>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="border-t-2 border-line-strong pt-4 text-h3 text-ink">
              What we cannot
            </h3>
            <div className="mt-4 space-y-3 text-sm text-ink-body">
              <p>
                We cannot promise that an ambulance, the fire service or the police will
                arrive, or how quickly. Siren notifies them; what happens next is not
                ours to commit to.
              </p>
              <p>
                We cannot watch an area no coordinator is covering. Confirmation runs
                during published hours, and outside them Siren says so plainly instead of
                implying someone is reading.
              </p>
              <p>
                We do not dispatch responders, and we do not tell you help is on the way.
                Any alert you get from us describes only what Siren itself did.
              </p>
            </div>
            <p className="mt-5 border-t border-line pt-4 text-sm text-ink-body">
              In a life-threatening emergency, call{' '}
              <strong className="font-semibold text-ink">767</strong> or{' '}
              <strong className="font-semibold text-ink">112</strong> as well.
            </p>
          </div>
        </div>
      </Container>
    </section>
  )
}

/* ── The public record ─────────────────────────────────────────────────── */

function Record() {
  const { data: incidents = [], isLoading, isError } = useQuery<Incident[]>({
    queryKey: ['active-incidents'],
    queryFn: getActiveIncidents,
    refetchInterval: 60_000,
  })

  return (
    <section
      aria-labelledby="record-heading"
      className="border-b border-line bg-canvas py-14 sm:py-section"
    >
      <Container>
        <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
          <div className="max-w-[48ch]">
            <h2 id="record-heading" className="text-h1 text-ink sm:text-display">
              Everything Siren has confirmed is public.
            </h2>
            <p className="mt-4 max-w-[54ch] text-body-lg text-ink-body">
              Each confirmed incident keeps its own page, showing the steps above with the
              time each one actually happened.
            </p>
          </div>
          <Link
            to="/feed"
            className="text-sm font-semibold text-primary-700 underline decoration-primary-200 decoration-2 underline-offset-4 hover:decoration-primary-700"
          >
            See every incident
          </Link>
        </div>

        <div className="mt-9">
          {isLoading && (
            <ul className="divide-y divide-line border-y border-line">
              {[0, 1, 2].map((i) => (
                <li key={i} className="py-4">
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="mt-2.5 h-5 w-56" />
                </li>
              ))}
            </ul>
          )}

          {isError && (
            <EmptyState
              icon={Activity}
              title="The incident feed is unavailable right now"
              description="We could not reach it. This page will pick the feed back up on its own shortly."
            />
          )}

          {!isLoading && !isError && incidents.length === 0 && (
            <EmptyState
              icon={CheckCircle2}
              title="Nothing is open right now"
              description="No confirmed incident is currently active in the areas Siren covers. New ones appear here as coordinators confirm them."
              action={
                <ButtonLink to="/feed" variant="secondary" size="sm">
                  Read past incidents
                </ButtonLink>
              }
            />
          )}

          {/*
            A record reads as a list, not as a grid of cards: the rows share a
            scale so two incidents can be compared down the column.
          */}
          {!isLoading && !isError && incidents.length > 0 && (
            <ul className="divide-y divide-line border-y border-line">
              {incidents.slice(0, 6).map((incident) => (
                <li key={incident.id}>
                  <Link
                    to={`/track/${incident.id}`}
                    className="group flex flex-col gap-2 py-4 transition-colors duration-fast hover:bg-surface sm:flex-row sm:items-baseline sm:gap-6"
                  >
                    <p className="order-2 shrink-0 font-command text-caption text-ink-faint sm:order-1 sm:w-28">
                      {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}
                    </p>
                    <div className="order-1 min-w-0 flex-1 sm:order-2">
                      <h3 className="text-h3 text-ink group-hover:underline">
                        {incidentTypeLabel(incident.incident_type)}
                        {incident.zone_name && (
                          <span className="font-normal text-ink-muted"> in {incident.zone_name}</span>
                        )}
                      </h3>
                      <p className="mt-1 line-clamp-2 max-w-[62ch] text-sm text-ink-body">
                        {incident.description}
                      </p>
                    </div>
                    <div className="order-3 flex shrink-0 items-center gap-2">
                      <StatusPill status={incident.status} size="sm" />
                      <SeverityTag severity={incident.severity} />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Container>
    </section>
  )
}

/* ── Join ──────────────────────────────────────────────────────────────── */

/**
 * The commands are set in mono because a resident has to type them exactly.
 * That is the only place mono appears in the product.
 */
function Join() {
  const { waLink } = useWhatsApp()

  return (
    <section aria-labelledby="join-heading" className="bg-night py-14 sm:py-section">
      <Container>
        <div className="grid gap-10 lg:grid-cols-[1fr_24rem] lg:gap-20">
          <div>
            <h2
              id="join-heading"
              className="max-w-[40ch] text-h1 font-extrabold text-ink-invert sm:text-display"
            >
              Hear about it from a person who checked.
            </h2>
            <p className="mt-4 max-w-[52ch] text-body-lg text-primary-100">
              Subscribe to the LGA you live in. You will only ever get a message a
              coordinator has confirmed, and you can leave at any time.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <ButtonLink
                href={waLink('WATCH Oshodi-Isolo')}
                target="_blank"
                rel="noopener noreferrer"
                variant="inverse"
                size="lg"
              >
                Subscribe on WhatsApp
              </ButtonLink>
              <ButtonLink
                to="/#how-it-works"
                size="lg"
                className="border border-primary-400 bg-transparent text-ink-invert hover:bg-primary-600"
              >
                Read it again
              </ButtonLink>
            </div>
          </div>

          <dl className="space-y-4 self-end border-t border-primary-600 pt-6">
            {[
              { cmd: 'WATCH Oshodi-Isolo', desc: 'Start getting alerts for that LGA' },
              { cmd: 'LIST', desc: 'See which areas you are subscribed to' },
              { cmd: 'STOP Oshodi-Isolo', desc: 'Leave that one area' },
              { cmd: 'PIDGIN', desc: 'Switch the messages to Pidgin' },
            ].map((c) => (
              <div key={c.cmd}>
                <dt className="font-command text-sm text-ink-invert">{c.cmd}</dt>
                <dd className="mt-0.5 text-caption text-primary-200">{c.desc}</dd>
              </div>
            ))}
          </dl>
        </div>
      </Container>
    </section>
  )
}

/* ── Page ──────────────────────────────────────────────────────────────── */

export default function HomePage() {
  return (
    <div className="min-h-screen bg-canvas">
      <Nav />
      <main id="main">
        <Hero />
        <Why />
        <Sequence />
        <PromiseBoundary />
        <Record />
        <Join />
      </main>
      <Footer />
    </div>
  )
}
