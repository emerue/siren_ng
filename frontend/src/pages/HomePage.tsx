import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  MessageSquare,
  ShieldCheck,
  Users,
  Landmark,
  CheckCircle2,
  ArrowRight,
  MapPin,
  Activity,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { getActiveIncidents } from '../api'
import type { Incident } from '../types'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import { ButtonLink } from '../components/ui/Button'
import { Container, Section, SectionHeading, Card, Skeleton, EmptyState } from '../components/ui/Primitives'
import { StatusPill, SeverityTag } from '../components/ui/StatusPill'
import { waLink } from '../lib/whatsapp'
import { incidentTypeLabel } from '../lib/incident'

/**
 * Landing page.
 *
 * The web layer is an explanation and trust surface, not the emergency
 * reporting app — reporting happens on WhatsApp (BRD §45). The page therefore
 * answers, in order: what is this → why care → how it works → why trust it →
 * what Siren actually promises → what to do next.
 *
 * Deliberately absent (BRD §5.2/§5.3): donations, resource boards, historical
 * data, zone safety scores, Guardian/Commute surfaces.
 */

/* ── Hero ──────────────────────────────────────────────────────────────── */

function HeroVisual() {
  return (
    <div className="relative" aria-hidden="true">
      <Card className="overflow-hidden shadow-md">
        {/* Inbound report */}
        <div className="border-b border-line bg-sunken/60 px-4 py-3">
          <p className="text-overline uppercase text-ink-faint">Resident → Siren</p>
        </div>
        <div className="space-y-3 px-4 py-4">
          <div className="max-w-[85%] rounded-lg rounded-tl-sm bg-sunken px-3.5 py-2.5">
            <p className="text-sm text-ink-body">Fire for Isolo market, near the bus stop</p>
            <p className="mt-1 text-overline text-ink-faint">11:04</p>
          </div>
          <div className="max-w-[85%] rounded-lg rounded-tl-sm bg-sunken px-3.5 py-2.5">
            <p className="text-sm text-ink-body">Received — a coordinator is confirming it now.</p>
            <p className="mt-1 text-overline text-ink-faint">11:04</p>
          </div>
        </div>

        {/* Human verification — the pivot of the whole product */}
        <div className="flex items-center gap-2.5 border-y border-line bg-primary-50 px-4 py-3">
          <ShieldCheck className="h-4 w-4 shrink-0 text-primary-700" />
          <p className="text-caption font-semibold text-primary-700">
            Confirmed by a Siren coordinator · 6 min
          </p>
        </div>

        {/* Outbound alert */}
        <div className="px-4 py-4">
          <p className="mb-2.5 text-overline uppercase text-ink-faint">Siren → Neighbours in Oshodi-Isolo</p>
          <div className="rounded-lg border border-line bg-surface px-3.5 py-3">
            <div className="flex items-center gap-2">
              <SeverityTag severity="HIGH" />
              <span className="text-caption font-semibold text-ink">Fire · Oshodi-Isolo</span>
            </div>
            <p className="mt-2 text-caption text-ink-body">
              Confirmed by a Siren coordinator. Your neighbours here have been alerted and
              emergency services notified.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}

function Hero() {
  return (
    <section className="border-b border-line bg-surface">
      <Container className="py-14 sm:py-20">
        <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_1fr] lg:gap-16">
          <div>
            <p className="mb-4 inline-flex items-center gap-2 rounded-md bg-sunken px-2.5 py-1 text-overline uppercase text-ink-muted">
              <MapPin className="h-3 w-3" aria-hidden="true" />
              Piloting in Oshodi-Isolo, Lagos
            </p>

            {/*
              Headline stays at display-lg rather than display-xl: in the hero's
              ~560px column, 3.5rem broke to five ragged lines and read as shouting.
            */}
            <h1 className="text-display sm:text-display-lg text-ink">
              When something happens on your street, your neighbours should know.
            </h1>

            <p className="mt-5 max-w-xl text-body-lg text-ink-body">
              Report an emergency on WhatsApp. A Siren coordinator confirms it is real,
              then everyone subscribed in your LGA is alerted — and emergency services
              are notified.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <ButtonLink
                href={waLink('I want to report an emergency')}
                target="_blank"
                rel="noopener noreferrer"
                size="lg"
              >
                Report on WhatsApp
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </ButtonLink>
              <ButtonLink to="/connect" variant="secondary" size="lg">
                Get alerts for your area
              </ButtonLink>
            </div>

            <p className="mt-5 text-caption text-ink-muted">
              No app to install. No account. Works on WhatsApp.
            </p>
          </div>

          <HeroVisual />
        </div>
      </Container>
    </section>
  )
}

/* ── Problem ───────────────────────────────────────────────────────────── */

function Problem() {
  return (
    <Section labelledBy="problem-heading">
      <Container>
        <SectionHeading
          id="problem-heading"
          eyebrow="Why this exists"
          title="In an emergency, most people call someone they know — not a hotline."
          lede="Word of mouth is fast but unverified. Official lines are overwhelmed. Siren adds verification and structure to the response that already happens on your street."
        />

        <dl className="mt-10 grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-3">
          {[
            {
              stat: '78%',
              label: 'call family, friends or neighbours first in a medical emergency',
              source: 'Emergency Response Africa survey',
            },
            {
              stat: '~3%',
              label: 'call an ambulance as their first action',
              source: 'Emergency Response Africa survey',
            },
            {
              stat: '~95%',
              label: 'of Nigerian internet users are reachable on WhatsApp',
              source: 'Nigerian internet usage data',
            },
          ].map((s) => (
            <div key={s.stat} className="bg-surface p-6">
              <dt className="text-display text-ink">{s.stat}</dt>
              <dd className="mt-1.5 text-sm text-ink-body">
                {s.label}
                <span className="mt-2 block text-overline uppercase text-ink-faint">{s.source}</span>
              </dd>
            </div>
          ))}
        </dl>
      </Container>
    </Section>
  )
}

/* ── How it works ──────────────────────────────────────────────────────── */

const STEPS = [
  {
    icon: MessageSquare,
    title: 'Report',
    body: 'Send what you saw to the Siren number on WhatsApp — English or Pidgin, however short. A photo helps but is not required.',
  },
  {
    icon: ShieldCheck,
    title: 'A coordinator confirms',
    body: 'Reports are sorted automatically to speed up review, but a named Siren coordinator decides what is real. Nothing is broadcast without them.',
  },
  {
    icon: Users,
    title: 'Neighbours are alerted',
    body: 'Everyone subscribed to that LGA gets a WhatsApp alert saying what happened and where.',
  },
  {
    icon: Landmark,
    title: 'Emergency services notified',
    body: 'Siren forwards every confirmed incident to official channels. We tell you we sent it — we never promise what they will do.',
  },
  {
    icon: CheckCircle2,
    title: 'The loop closes',
    body: 'When the incident is over, the person who reported it is told, and the record stays open to view.',
  },
]

function HowItWorks() {
  return (
    <Section tone="surface" id="how-it-works" labelledBy="how-heading">
      <Container>
        <SectionHeading
          id="how-heading"
          eyebrow="How it works"
          title="One report, five steps, no guesswork."
          lede="Every step is something Siren actually does — you can watch it happen on the incident page."
        />

        <ol className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {STEPS.map((step, i) => {
            const Icon = step.icon
            return (
              <li key={step.title} className="relative rounded-lg bg-sunken/70 p-5">
                <span className="flex h-9 w-9 items-center justify-center rounded-md bg-surface text-primary-700 shadow-xs">
                  <Icon className="h-4.5 w-4.5" aria-hidden="true" />
                </span>
                <p className="mt-4 text-overline uppercase text-ink-faint">Step {i + 1}</p>
                {/* text-sm, not h3: in a 5-up rail the larger size wrapped every
                    title onto two ragged lines and broke the horizontal rhythm. */}
                <h3 className="mt-1 text-sm font-semibold text-ink">{step.title}</h3>
                <p className="mt-1.5 text-caption text-ink-body">{step.body}</p>
              </li>
            )
          })}
        </ol>
      </Container>
    </Section>
  )
}

/* ── Trust ─────────────────────────────────────────────────────────────── */

function Trust() {
  return (
    <Section labelledBy="trust-heading">
      <Container>
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <SectionHeading
              id="trust-heading"
              eyebrow="Why you can trust it"
              title="A person decides what gets sent to your neighbours."
              lede="False alarms spread panic and destroy trust — so speed never overrides verification. Software sorts reports to make review fast; a human confirms every single one before anyone is alerted."
            />
            <div className="mt-7 space-y-3">
              {[
                'An unverified report reaches no one but the coordinator.',
                'Every alert says who confirmed it and when.',
                'Your phone number is never shown in an alert or on the site.',
              ].map((line) => (
                <div key={line} className="flex gap-2.5">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-status-resolved" aria-hidden="true" />
                  <p className="text-sm text-ink-body">{line}</p>
                </div>
              ))}
            </div>
          </div>

          {/* The promise boundary, stated as plainly as we can put it. */}
          <Card className="self-start p-6 sm:p-7">
            <h3 className="text-h3 text-ink">What Siren promises — and what it does not</h3>
            <dl className="mt-5 space-y-4">
              <div>
                <dt className="text-overline uppercase text-status-resolved">What we do</dt>
                <dd className="mt-1.5 text-sm text-ink-body">
                  We confirm the report, alert subscribed neighbours in that LGA, notify
                  emergency services, and tell you when it is resolved.
                </dd>
              </div>
              <div className="border-t border-line pt-4">
                <dt className="text-overline uppercase text-ink-muted">What we cannot promise</dt>
                <dd className="mt-1.5 text-sm text-ink-body">
                  We cannot promise that an ambulance, the fire service or the police will
                  arrive. Siren is not an emergency service, and we will never suggest
                  otherwise.
                </dd>
              </div>
            </dl>
            <p className="mt-5 rounded-md bg-sunken px-3.5 py-3 text-caption text-ink-body">
              In a life-threatening emergency, call <strong className="font-semibold text-ink">767</strong> or{' '}
              <strong className="font-semibold text-ink">112</strong> as well.
            </p>
          </Card>
        </div>
      </Container>
    </Section>
  )
}

/* ── Live incidents ────────────────────────────────────────────────────── */

function LiveIncidents() {
  const { data: incidents = [], isLoading, isError } = useQuery<Incident[]>({
    queryKey: ['active-incidents'],
    queryFn: getActiveIncidents,
    refetchInterval: 60_000,
  })

  return (
    <Section tone="surface" labelledBy="live-heading">
      <Container>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <SectionHeading
            id="live-heading"
            eyebrow="Transparency"
            title="See what Siren has actually done."
            lede="Every confirmed incident has a public page showing each step we took, and when."
            className="mb-0"
          />
          <Link
            to="/feed"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary-700 hover:underline"
          >
            All incidents
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>

        <div className="mt-8">
          {isLoading && (
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <li key={i}>
                  <Card className="p-5">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="mt-3 h-5 w-40" />
                    <Skeleton className="mt-2 h-4 w-full" />
                  </Card>
                </li>
              ))}
            </ul>
          )}

          {isError && (
            <EmptyState
              icon={Activity}
              title="Live incidents are unavailable right now"
              description="We could not reach the incident feed. It should return shortly."
            />
          )}

          {!isLoading && !isError && incidents.length === 0 && (
            <EmptyState
              icon={CheckCircle2}
              title="No active incidents"
              description="Nothing is currently open in the areas Siren covers. Confirmed incidents appear here as they happen."
              action={
                <ButtonLink to="/feed" variant="secondary" size="sm">
                  View past incidents
                </ButtonLink>
              }
            />
          )}

          {!isLoading && !isError && incidents.length > 0 && (
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {incidents.slice(0, 6).map((incident) => (
                <li key={incident.id}>
                  <Card interactive as="article" className="h-full">
                    <Link to={`/track/${incident.id}`} className="block h-full p-5">
                      <div className="flex items-center gap-2">
                        <StatusPill status={incident.status} size="sm" />
                        <SeverityTag severity={incident.severity} />
                      </div>
                      <h3 className="mt-3 text-h3 text-ink">
                        {incidentTypeLabel(incident.incident_type)}
                        {incident.zone_name && (
                          <span className="font-normal text-ink-muted"> · {incident.zone_name}</span>
                        )}
                      </h3>
                      <p className="mt-1.5 line-clamp-2 text-caption text-ink-body">
                        {incident.description}
                      </p>
                      <p className="mt-3 text-overline uppercase text-ink-faint">
                        {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}
                      </p>
                    </Link>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Container>
    </Section>
  )
}

/* ── Closing CTA ───────────────────────────────────────────────────────── */

function ClosingCTA() {
  return (
    <Section labelledBy="cta-heading">
      <Container>
        <div className="rounded-xl bg-primary-700 px-6 py-12 sm:px-12 sm:py-14">
          <div className="max-w-prose">
            <h2 id="cta-heading" className="text-h1 sm:text-display text-ink-invert">
              Get alerts for the area you live in.
            </h2>
            <p className="mt-4 text-body-lg text-primary-100">
              Send <strong className="font-semibold text-ink-invert">WATCH</strong> and your LGA — for
              example <strong className="font-semibold text-ink-invert">WATCH Oshodi-Isolo</strong> — to the
              Siren number on WhatsApp. Send <strong className="font-semibold text-ink-invert">STOP</strong> any
              time to leave.
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
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </ButtonLink>
              <ButtonLink
                to="/#how-it-works"
                variant="ghost"
                size="lg"
                className="text-primary-100 hover:bg-primary-600 hover:text-ink-invert"
              >
                Read how it works
              </ButtonLink>
            </div>
          </div>
        </div>
      </Container>
    </Section>
  )
}

/* ── Page ──────────────────────────────────────────────────────────────── */

export default function HomePage() {
  return (
    <div className="min-h-screen bg-canvas">
      <Nav />
      <main id="main">
        <Hero />
        <Problem />
        <HowItWorks />
        <Trust />
        <LiveIncidents />
        <ClosingCTA />
      </main>
      <Footer />
    </div>
  )
}
