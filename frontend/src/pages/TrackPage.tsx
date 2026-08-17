import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker } from 'react-leaflet'
import L from 'leaflet'
import { format, formatDistanceToNow } from 'date-fns'
import { ArrowLeft, Link2, Check, ImageOff, MapPin } from 'lucide-react'
import { getIncident } from '../api'
import { useWebSocket } from '../hooks/useWebSocket'
import { useFeatures } from '../hooks/useFeatures'
import type { Incident, IncidentMedia } from '../types'
import Nav from '../components/Nav'
import Footer from '../components/Footer'
import IncidentTimeline from '../components/IncidentTimeline'
import { Button } from '../components/ui/Button'
import { Container, Card, Skeleton, EmptyState, ErrorState } from '../components/ui/Primitives'
import { StatusPill, SeverityTag, statusMeta } from '../components/ui/StatusPill'
import { incidentTypeLabel } from '../lib/incident'

delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

/**
 * Public incident page — the product's transparency surface.
 *
 * It answers one question honestly: what has Siren actually done about this?
 * Anything that would imply a third-party response is deliberately absent
 * (§8), and features that are OUT/HIDDEN in the v8 MVP (§5.2/§5.3) render only
 * when their feature flag is on.
 */

function CopyLinkButton() {
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!copied) return
    const t = setTimeout(() => setCopied(false), 2000)
    return () => clearTimeout(t)
  }, [copied])

  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(window.location.href)
          setCopied(true)
        } catch {
          /* clipboard unavailable — nothing useful to say to the user */
        }
      }}
    >
      {copied ? <Check className="h-4 w-4" aria-hidden="true" /> : <Link2 className="h-4 w-4" aria-hidden="true" />}
      {copied ? 'Link copied' : 'Copy link'}
    </Button>
  )
}

function MediaStrip({ media }: { media: IncidentMedia[] }) {
  const images = media.filter((m) => m.media_type === 'image')
  const [failed, setFailed] = useState<Record<string, boolean>>({})

  if (images.length === 0) {
    return (
      <p className="flex items-center gap-2 text-caption text-ink-muted">
        <ImageOff className="h-4 w-4" aria-hidden="true" />
        No photos were attached to this report.
      </p>
    )
  }

  return (
    <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
      {images.map((m) => (
        <li key={m.id}>
          <a
            href={m.public_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block overflow-hidden rounded-md border border-line bg-sunken"
          >
            {failed[m.id] ? (
              <div className="flex aspect-[4/3] items-center justify-center text-ink-faint">
                <ImageOff className="h-5 w-5" aria-hidden="true" />
              </div>
            ) : (
              <img
                src={m.public_url}
                alt="Photo submitted with this incident report"
                loading="lazy"
                decoding="async"
                width={400}
                height={300}
                className="aspect-[4/3] w-full object-cover"
                onError={() => setFailed((f) => ({ ...f, [m.id]: true }))}
              />
            )}
          </a>
        </li>
      ))}
    </ul>
  )
}

function LoadingSkeleton() {
  return (
    <Container size="prose" className="py-8">
      <Skeleton className="h-4 w-28" />
      <Card className="mt-4 p-6">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="mt-3 h-8 w-64" />
        <Skeleton className="mt-3 h-4 w-full" />
        <Skeleton className="mt-2 h-4 w-3/4" />
      </Card>
      <Card className="mt-4 p-6">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="mb-5 flex gap-3">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div className="flex-1">
              <Skeleton className="h-4 w-44" />
              <Skeleton className="mt-2 h-3 w-full" />
            </div>
          </div>
        ))}
      </Card>
    </Container>
  )
}

export default function TrackPage() {
  const { id } = useParams<{ id: string }>()
  const { isOn } = useFeatures()
  useWebSocket()

  const { data: incident, isLoading, isError, refetch } = useQuery<Incident>({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id!),
    refetchInterval: 30_000,
    enabled: !!id,
  })

  // Keep the tab title meaningful when someone shares or bookmarks the link.
  useEffect(() => {
    if (!incident) return
    const where = incident.zone_name || 'Lagos'
    document.title = `${incidentTypeLabel(incident.incident_type)} · ${where} — Siren.ng`
    return () => {
      document.title = 'Siren.ng — Verified emergency alerts for Lagos neighbourhoods'
    }
  }, [incident])

  const meta = incident ? statusMeta(incident.status) : null

  return (
    <div className="min-h-screen bg-canvas">
      <Nav />

      <main id="main">
        {isLoading && <LoadingSkeleton />}

        {isError && (
          <Container size="prose" className="py-12">
            <ErrorState
              title="We could not load this incident"
              description="The link may be wrong, or the incident feed is temporarily unavailable."
              onRetry={() => refetch()}
            />
          </Container>
        )}

        {!isLoading && !isError && !incident && (
          <Container size="prose" className="py-12">
            <EmptyState
              icon={MapPin}
              title="Incident not found"
              description="This incident does not exist or is no longer public."
            />
          </Container>
        )}

        {incident && meta && (
          <Container size="prose" className="py-8 sm:py-10">
            <Link
              to="/feed"
              className="inline-flex items-center gap-1.5 text-caption font-medium text-ink-muted transition-colors duration-fast hover:text-primary-700"
            >
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
              All incidents
            </Link>

            {/* Header: what, where, and exactly how far along it is */}
            <Card className="mt-4 p-6">
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill status={incident.status} />
                <SeverityTag severity={incident.severity} />
              </div>

              <h1 className="mt-4 text-h1 sm:text-display text-ink">
                {incidentTypeLabel(incident.incident_type)}
                {incident.zone_name && (
                  <span className="font-normal text-ink-muted"> · {incident.zone_name}</span>
                )}
              </h1>

              <p className="mt-2.5 text-sm text-ink-body">{meta.description}</p>

              <dl className="mt-5 flex flex-wrap gap-x-8 gap-y-3 border-t border-line pt-5">
                <div>
                  <dt className="text-overline uppercase text-ink-faint">Reported</dt>
                  <dd className="mt-0.5 text-caption text-ink-body">
                    <time dateTime={incident.created_at}>
                      {format(new Date(incident.created_at), 'd MMM yyyy, HH:mm')}
                    </time>
                    <span className="text-ink-faint">
                      {' · '}
                      {formatDistanceToNow(new Date(incident.created_at), { addSuffix: true })}
                    </span>
                  </dd>
                </div>
                {incident.address_text && (
                  <div>
                    <dt className="text-overline uppercase text-ink-faint">Location given</dt>
                    <dd className="mt-0.5 text-caption text-ink-body">{incident.address_text}</dd>
                  </div>
                )}
              </dl>

              <div className="mt-5 flex flex-wrap gap-2">
                <CopyLinkButton />
              </div>
            </Card>

            {/* The report itself */}
            <Card className="mt-4 p-6">
              <h2 className="text-h3 text-ink">What was reported</h2>
              <p className="mt-2.5 whitespace-pre-line text-sm text-ink-body">{incident.description}</p>
              <div className="mt-5 border-t border-line pt-5">
                <h3 className="mb-3 text-overline uppercase text-ink-faint">Photos</h3>
                <MediaStrip media={incident.media ?? []} />
              </div>
            </Card>

            {/* The trust surface: what Siren did, step by step */}
            <Card className="mt-4 p-6">
              <h2 className="text-h3 text-ink">What Siren has done</h2>
              <p className="mt-1.5 text-caption text-ink-muted">
                Each step below is an action Siren took. Steps that have not happened are shown greyed out.
              </p>
              <div className="mt-6">
                <IncidentTimeline
                  status={incident.status}
                  logs={incident.response_logs ?? []}
                  createdAt={incident.created_at}
                />
              </div>
            </Card>

            {/* Map — only when we genuinely have coordinates */}
            {incident.location_lat && incident.location_lng && (
              <Card className="mt-4 overflow-hidden">
                <div className="border-b border-line px-6 py-4">
                  <h2 className="text-h3 text-ink">Approximate location</h2>
                </div>
                <div className="h-56">
                  <MapContainer
                    center={[incident.location_lat, incident.location_lng]}
                    zoom={15}
                    style={{ height: '100%', width: '100%' }}
                    zoomControl={false}
                    scrollWheelZoom={false}
                  >
                    <TileLayer
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      attribution="&copy; OpenStreetMap contributors"
                    />
                    <Marker position={[incident.location_lat, incident.location_lng]} />
                  </MapContainer>
                </div>
              </Card>
            )}

            {/*
              Resource board and donations are OUT of the v8 MVP (§5.3) and
              render only if their flags are enabled. Their full UIs were
              removed with the v8 scope cut; re-enable deliberately.
            */}
            {isOn('resource_boards') && (
              <Card className="mt-4 p-6">
                <h2 className="text-h3 text-ink">Resource board</h2>
                <p className="mt-1.5 text-caption text-ink-muted">
                  This feature is enabled but its interface has not been rebuilt for v8.
                </p>
              </Card>
            )}

            <p className="mt-8 rounded-md bg-sunken px-4 py-3.5 text-caption text-ink-body">
              Siren alerts neighbours and notifies emergency services. Siren cannot guarantee
              that emergency services will arrive. In a life-threatening emergency, call{' '}
              <strong className="font-semibold text-ink">767</strong> or{' '}
              <strong className="font-semibold text-ink">112</strong>.
            </p>
          </Container>
        )}
      </main>

      <Footer />
    </div>
  )
}
