import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
})

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Incidents ─────────────────────────────────────────────────────────────────
export const getActiveIncidents = () =>
  api.get('/api/incidents/active/').then((r) => r.data)

export const getIncidents = (params?: Record<string, string>) =>
  api.get('/api/incidents/', { params }).then((r) => r.data)

export const getIncident = (id: string) =>
  api.get(`/api/incidents/${id}/`).then((r) => r.data)

export const trackIncident = (id: string) =>
  api.get(`/api/incidents/${id}/track/`).then((r) => r.data)

export const vouchIncident = (id: string, data: { lat?: number; lng?: number; session_hash?: string }) =>
  api.post(`/api/incidents/${id}/vouch/`, data).then((r) => r.data)

export const dispatchIncident = (id: string) =>
  api.patch(`/api/incidents/${id}/dispatch/`).then((r) => r.data)

export const resolveIncident = (id: string) =>
  api.patch(`/api/incidents/${id}/resolve/`).then((r) => r.data)

export const webIngest = (data: Record<string, unknown>) =>
  api.post('/api/ingest/web/', data).then((r) => r.data)

// ── Media ─────────────────────────────────────────────────────────────────────
export const getIncidentMedia = (incidentId: string) =>
  api.get(`/api/incidents/${incidentId}/media/list/`).then((r) => r.data)

export const uploadMedia = (incidentId: string, files: File | File[]) => {
  const form = new FormData()
  const fileArray = Array.isArray(files) ? files : [files]
  fileArray.forEach(f => form.append('files', f))
  return api.post(`/api/incidents/${incidentId}/media/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const deleteMedia = (incidentId: string, mediaId: number) =>
  api.delete(`/api/incidents/${incidentId}/media/${mediaId}/`).then((r) => r.data)

export const addMediaUrl = (incidentId: string, url: string) =>
  api.post(`/api/incidents/${incidentId}/media-urls/`, { url }).then((r) => r.data)

export const removeMediaUrl = (incidentId: string, url: string) =>
  api.delete(`/api/incidents/${incidentId}/media-urls/`, { data: { url } }).then((r) => r.data)

// ── Resources ─────────────────────────────────────────────────────────────────
export const getResources = (incidentId: string) =>
  api.get('/api/resources/', { params: { incident: incidentId } }).then((r) => r.data)

export const suggestResource = (data: Record<string, unknown>) =>
  api.post('/api/resources/', data).then((r) => r.data)

export const claimResource = (id: string, data: Record<string, unknown>) =>
  api.post(`/api/resources/${id}/claim/`, data).then((r) => r.data)

export const confirmResource = (id: string, data: Record<string, unknown>) =>
  api.post(`/api/resources/${id}/confirm/`, data).then((r) => r.data)

export const initiateDonation = (data: Record<string, unknown>) =>
  api.post('/api/resources/donate/', data).then((r) => r.data)

export const getDonationSummary = (incidentId: string) =>
  api.get('/api/resources/donations/', { params: { incident: incidentId } }).then((r) => r.data)

// ── Subscriptions ─────────────────────────────────────────────────────────────
export const createSubscription = (data: Record<string, unknown>) =>
  api.post('/api/subscriptions/', data).then((r) => r.data)

export const getSubscriptions = (phoneHash: string) =>
  api.get('/api/subscriptions/', { params: { phone_hash: phoneHash } }).then((r) => r.data)

export const updateSubscription = (id: string, data: Record<string, unknown>) =>
  api.patch(`/api/subscriptions/${id}/`, data).then((r) => r.data)

export const deleteSubscription = (id: string) =>
  api.delete(`/api/subscriptions/${id}/`).then((r) => r.data)

export const createCommuteSubscription = (data: Record<string, unknown>) =>
  api.post('/api/subscriptions/commute/', data).then((r) => r.data)

export const getMyImpact = (phoneHash: string) =>
  api.get('/api/subscriptions/my-impact/', { params: { phone_hash: phoneHash } }).then((r) => r.data)

// ── Organisations ─────────────────────────────────────────────────────────────
export const getOrganisationsMap = () =>
  api.get('/api/organisations/map/').then((r) => r.data)

export const registerOrganisation = (data: Record<string, unknown>) =>
  api.post('/api/organisations/register/', data).then((r) => r.data)

export const registerResponder = (data: Record<string, unknown>) =>
  api.post('/api/responders/register/', data).then((r) => r.data)

// ── Analytics (JWT) ───────────────────────────────────────────────────────────
export const getAnalyticsSummary = (range = '7d') =>
  api.get('/api/analytics/summary/', { params: { range } }).then((r) => r.data)

export const getAnalyticsZones = (range = '7d') =>
  api.get('/api/analytics/zones/', { params: { range } }).then((r) => r.data)

export const getAnalyticsTrends = (range = '7d') =>
  api.get('/api/analytics/trends/', { params: { range } }).then((r) => r.data)

export const getAnalyticsDonations = (range = '7d') =>
  api.get('/api/analytics/donations/', { params: { range } }).then((r) => r.data)

export const getAnalyticsSubscribers = (range = '7d') =>
  api.get('/api/analytics/subscribers/', { params: { range } }).then((r) => r.data)

// ── Historical data ────────────────────────────────────────────────────────────
export const getHistoricalIncidents = (params?: Record<string, string>) =>
  api.get('/api/incidents/', { params: { historical: 'true', ...params } }).then((r) => r.data)

export const getZoneHistory = (params: { zoneName?: string; lat?: number; lng?: number; radiusKm?: number }) => {
  const p: Record<string, string | number> = {}
  if (params.zoneName) p.zone_name = params.zoneName
  if (params.lat != null) p.lat = params.lat
  if (params.lng != null) p.lng = params.lng
  if (params.radiusKm != null) p.radius_km = params.radiusKm
  return api.get('/api/incidents/zone-history/', { params: p }).then((r) => r.data)
}

export const getZoneStats = () =>
  api.get('/api/incidents/zone-stats/').then((r) => r.data)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const loginUser = (credentials: { username: string; password: string }) =>
  api.post('/api/auth/token/', credentials).then((r) => r.data)

export const refreshToken = (refresh: string) =>
  api.post('/api/auth/token/refresh/', { refresh }).then((r) => r.data)

export default api
