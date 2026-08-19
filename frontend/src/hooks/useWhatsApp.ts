import { useQuery } from '@tanstack/react-query'
import { getSiteConfig } from '../api'
import { WHATSAPP_NUMBER as BUILD_TIME_FALLBACK, buildWaLink } from '../lib/whatsapp'

/**
 * The Siren WhatsApp number, resolved at RUNTIME from GET /api/config/.
 *
 * Vite inlines `import.meta.env.*` at build time, and the Docker frontend
 * stage never receives Railway's service variables — so the placeholder
 * fallback was being compiled into the production bundle. Fetching the number
 * instead means changing it is an env var + restart, with no rebuild.
 *
 * Falls back to the build-time value until the request resolves.
 */
export function useWhatsApp() {
  const { data } = useQuery({
    queryKey: ['site-config'],
    queryFn: getSiteConfig,
    staleTime: 60 * 60 * 1000,
    retry: 1,
  })

  const number = data?.whatsapp_number?.trim() || BUILD_TIME_FALLBACK

  return {
    number,
    /** Pre-filled WhatsApp deep link using the resolved number. */
    waLink: (text?: string) => buildWaLink(number, text),
  }
}
