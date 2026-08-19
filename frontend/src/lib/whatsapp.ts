/**
 * Siren is WhatsApp-first (BRD §1). The web layer's job is to explain, build
 * trust and hand people off to WhatsApp — so every outbound WhatsApp link is
 * built here rather than reconstructed per page.
 *
 * IMPORTANT: WHATSAPP_NUMBER below is a BUILD-TIME value and only a fallback.
 * Vite inlines import.meta.env at build time, and the Docker frontend stage
 * never receives Railway's service variables — which is why production shipped
 * the placeholder. Components should use the `useWhatsApp()` hook, which
 * resolves the real number at runtime from GET /api/config/.
 */
export const WHATSAPP_NUMBER =
  import.meta.env.VITE_WHATSAPP_NUMBER || '+2349000000000'

/** Build a wa.me deep link for an explicit number. */
export function buildWaLink(number: string, text?: string): string {
  const digits = String(number || '').replace(/[^\d]/g, '')
  const base = `https://wa.me/${digits}`
  return text ? `${base}?text=${encodeURIComponent(text)}` : base
}

/** Fallback-only link builder. Prefer useWhatsApp() inside components. */
export function waLink(text?: string): string {
  return buildWaLink(WHATSAPP_NUMBER, text)
}

export const WHATSAPP_DISPLAY = WHATSAPP_NUMBER
