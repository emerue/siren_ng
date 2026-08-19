/**
 * Incident types are stored as enums (FIRE, RTA…). Never show a raw enum to a
 * resident — shouting "FIRE" in caps is both unpolished and needlessly alarming.
 */
const TYPE_LABELS: Record<string, string> = {
  FIRE: 'Fire',
  FLOOD: 'Flood',
  COLLAPSE: 'Building collapse',
  RTA: 'Road accident',
  EXPLOSION: 'Explosion',
  DROWNING: 'Water emergency',
  HAZARD: 'Electrical hazard',
}

export function incidentTypeLabel(type?: string | null): string {
  if (!type) return 'Incident'
  return TYPE_LABELS[type] ?? type.charAt(0) + type.slice(1).toLowerCase()
}
