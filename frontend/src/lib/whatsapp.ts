/**
 * Siren is WhatsApp-first (BRD §1). The web layer's job is to explain, build
 * trust and hand people off to WhatsApp — so every outbound WhatsApp link is
 * built here rather than reconstructed per page.
 */
export const WHATSAPP_NUMBER = import.meta.env.VITE_WHATSAPP_NUMBER || '+2349000000000'

const DIGITS = WHATSAPP_NUMBER.replace(/[^\d]/g, '')

/** Pre-filled WhatsApp deep link. `text` becomes the drafted first message. */
export function waLink(text?: string): string {
  const base = `https://wa.me/${DIGITS}`
  return text ? `${base}?text=${encodeURIComponent(text)}` : base
}

/** Human-readable number for display next to the link. */
export const WHATSAPP_DISPLAY = WHATSAPP_NUMBER
