import { useQuery } from '@tanstack/react-query'
import { getFeatures } from '../api'

/**
 * v8 feature flags. Reads GET /api/features/ (backed by settings.FEATURES).
 * Flip a flag in Railway → Variables, restart, and the UI follows — no rebuild.
 *
 * Features are treated as OFF until loaded, so HIDDEN/OUT features never flash
 * on during the initial fetch.
 *
 *   const { isOn } = useFeatures()
 *   {isOn('donations') && <DonateLink />}
 */
export function useFeatures() {
  const { data } = useQuery({
    queryKey: ['features'],
    queryFn: getFeatures,
    staleTime: 5 * 60 * 1000,
  })
  const features = data ?? {}
  return { features, isOn: (name: string) => features[name] === true }
}
