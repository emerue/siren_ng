import { useQuery } from '@tanstack/react-query'
import { getSiteConfig } from '../api'
import { WHATSAPP_NUMBER as SYNC_NUMBER, buildWaLink } from '../lib/whatsapp'

/**
 * The public Siren line, sourced from SIREN_NG_MOBILE on the server.
 *
 * Django injects it into index.html, so `SYNC_NUMBER` is already correct on
 * first paint in production and this query simply confirms it. Under the Vite
 * dev server there is no injected config, so the fetch supplies it.
 *
 * Changing the number is an env var + restart — never a rebuild.
 */
export function useWhatsApp() {
  const { data } = useQuery({
    queryKey: ['site-config'],
    queryFn: getSiteConfig,
    staleTime: 60 * 60 * 1000,
    retry: 1,
    // Skip the request entirely when the server already told us.
    enabled: !SYNC_NUMBER,
  })

  const number = SYNC_NUMBER || data?.whatsapp_number?.trim() || ''

  return {
    number,
    /** True once a real number is known — use to avoid rendering a blank. */
    hasNumber: Boolean(number),
    waLink: (text?: string) => buildWaLink(number, text),
  }
}
