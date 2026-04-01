export interface ResponseLog {
  id: number
  incident: string
  from_status: string
  to_status: string
  actor: string
  note: string
  created_at: string
}

export interface VouchRecord {
  id: number
  incident: string
  session_hash: string
  voucher_lat: number | null
  voucher_lng: number | null
  distance_km: number | null
  is_suspicious: boolean
  source: 'WEB' | 'WHATSAPP'
  created_at: string
}

export interface IncidentMedia {
  id: number
  media_type: 'image' | 'video'
  public_url: string
  file_size: number
  upload_timestamp: string
}

export interface Incident {
  id: string
  source: 'WHATSAPP' | 'WEB'
  incident_type: string
  description: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  status: string
  location_lat: number | null
  location_lng: number | null
  address_text: string
  zone_name: string
  media_urls: string[]
  media?: IncidentMedia[]
  ai_confidence: number
  fraud_score: number
  ai_raw_response: Record<string, unknown>
  vouch_count: number
  vouch_threshold: number
  total_donations_kobo: number
  total_donations_naira: number
  donation_count: number
  is_infrastructure: boolean
  created_at: string
  updated_at: string
  resolved_at: string | null
  response_logs?: ResponseLog[]
}

export interface Responder {
  id: string
  name: string
  skill_category: string
  status: string
  home_lat: number
  home_lng: number
  response_radius_km: number
  is_available: boolean
  responds_to: string[]
  total_responses: number
  zone_name: string
  created_at: string
}

export interface ResponderDispatch {
  id: string
  responder: string
  responder_name: string
  incident: string
  incident_type: string
  notified_at: string
  accepted: boolean | null
  on_scene_at: string | null
  completed_at: string | null
}

export interface Organisation {
  id: string
  name: string
  org_type: string
  status: string
  location_lat: number
  location_lng: number
  address: string
  zone_name: string
  response_radius_km: number
  contact_name: string
  contact_whatsapp: string
  contact_phone: string
  responds_to: string[]
  operating_hours: string
  total_responses: number
  created_at: string
}

export interface ResourceClaim {
  id: string
  resource: string
  claimer_hash: string
  claimer_name: string
  claimer_phone: string
  claimed_at: string
}

export interface ResourceItem {
  id: string
  incident: string
  category: string
  label: string
  status: 'NEEDED' | 'CLAIMED' | 'ARRIVED'
  suggested_by_hash: string
  suggested_by_name: string
  suggested_via: string
  confirmed_by_hash: string
  confirmed_at: string | null
  created_at: string
  updated_at: string
  claim_count: number
  claims?: ResourceClaim[]
}

export interface Donation {
  id: string
  incident: string
  donor_name: string
  amount_kobo: number
  amount_naira: number
  fund_choice: 'VICTIM' | 'RESPONDER' | 'PLATFORM'
  status: string
  paystack_reference: string
  created_at: string
  confirmed_at: string | null
}

export interface DonationSummary {
  total_naira: number
  donation_count: number
  fund_breakdown: Record<string, number>
}

export interface LocationSubscription {
  id: string
  phone_hash: string
  whatsapp_number: string
  label: string
  subscription_type: 'POINT' | 'COMMUTE'
  location_type: string
  location_lat: number
  location_lng: number
  office_lat?: number
  office_lng?: number
  family_members: string[]
  alert_radius_km: number
  commute_buffer_km: number
  peak_only: boolean
  safety_score: number
  is_active: boolean
  incident_types: string[]
  created_at: string
  updated_at: string
}

export interface SafetyScoreLog {
  id: string
  subscription: string
  score: number
  reason: string
  created_at: string
}

export interface MyImpactData {
  subscriptions: Array<LocationSubscription & { score_logs: SafetyScoreLog[] }>
  total_alerts_received: number
  incidents_near_count: number
  incidents_resolved_near: number
  total_donations_on_alerted_incidents: number
  responders_triggered_count: number
}

export interface SubscriptionAlert {
  id: string
  subscription: string
  incident: string
  distance_km: number
  sent_at: string
  delivered: boolean
}

export interface ZoneHistory {
  zone_name: string
  total_incidents: number
  total_incidents_effective: number
  by_type: Record<string, number>
  by_year: Array<{ year: number; count: number }>
  resolution_rate: number
  avg_resolution_minutes: number | null
  trend: 'improving' | 'stable' | 'increasing'
  zone_score: number
  recent_5: Incident[]
}
