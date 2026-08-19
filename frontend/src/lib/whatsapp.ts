/**
 * Siren is WhatsApp-first (BRD §1). The web layer's job is to explain, build
 * trust and hand people off to WhatsApp, so every outbound WhatsApp link is
 * built here rather than reconstructed per page.
 *
 * The number comes from the SIREN_NG_MOBILE environment variable on the
 * server, resolved in this order:
 *
 *   1. window.__SIREN_CONFIG__  — injected into index.html by Django, so the
 *      correct number is present on FIRST paint with no network round-trip
 *   2. GET /api/config/         — used by the Vite dev server, which serves
 *      index.html itself and therefore has no injected config
 *   3. VITE_WHATSAPP_NUMBER     — build-time escape hatch, normally unset
 *
 * There is deliberately NO hardcoded fallback number: showing a plausible but
 * wrong number on an emergency service is worse than showing none.
 */
declare global {
  interface Window {
    __SIREN_CONFIG__?: { whatsapp_number?: string; site_url?: string }
  }
}

/** Number injected by the server, if this page was served by Django. */
export const INJECTED_NUMBER: string =
  (typeof window !== 'undefined' && window.__SIREN_CONFIG__?.whatsapp_number) || ''

/** Build-time override; normally empty (Vite inlines env at build time). */
export const BUILD_TIME_NUMBER: string =
  import.meta.env.VITE_WHATSAPP_NUMBER || ''

/** Best number available synchronously, before any fetch resolves. */
export const WHATSAPP_NUMBER = INJECTED_NUMBER || BUILD_TIME_NUMBER

/** Build a wa.me deep link for an explicit number. */
export function buildWaLink(number: string, text?: string): string {
  const digits = String(number || '').replace(/[^\d]/g, '')
  const base = digits ? `https://wa.me/${digits}` : 'https://wa.me'
  return text ? `${base}?text=${encodeURIComponent(text)}` : base
}

/** Non-reactive link builder. Prefer useWhatsApp() inside components. */
export function waLink(text?: string): string {
  return buildWaLink(WHATSAPP_NUMBER, text)
}

export const WHATSAPP_DISPLAY = WHATSAPP_NUMBER
