import { useQuery } from '@tanstack/react-query'
import api from '../api'
import DashboardLayout from '../components/DashboardLayout'
import type { Responder } from '../types'

export default function DashboardResponders() {
  const { data: responders = [], isLoading } = useQuery<Responder[]>({
    queryKey: ['all-responders'],
    queryFn: () => api.get('/api/responders/register/').then((r) => r.data).catch(() => []),
  })

  return (
    <DashboardLayout>
      <div className="p-8">
        <h1 className="text-2xl font-bold text-textPrimary mb-6">Responders</h1>

        {isLoading && <p className="text-textMuted">Loading...</p>}

        <div className="bg-white rounded-xl border border-border">
          <div className="px-6 py-4 border-b border-border font-semibold text-textPrimary">
            All Responders
          </div>
          {responders.length === 0 && !isLoading && (
            <p className="text-textMuted text-center py-8 text-sm">No responders yet.</p>
          )}
          <div className="divide-y divide-border">
            {responders.map((r) => (
              <div key={r.id} className="px-6 py-4 flex items-center gap-4">
                <div className="flex-1">
                  <div className="font-medium text-textPrimary text-sm">{r.name}</div>
                  <div className="text-textMuted text-xs">{r.skill_category} · {r.zone_name}</div>
                </div>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${r.status === 'VERIFIED' ? 'bg-green-100 text-green-700' : r.status === 'PENDING' ? 'bg-yellow-100 text-amber-700' : 'bg-gray-100 text-gray-500'}`}>
                  {r.status}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full border ${r.is_available ? 'border-green-400 text-green-700' : 'border-gray-300 text-gray-400'}`}>
                  {r.is_available ? 'Available' : 'Offline'}
                </span>
                <span className="text-textMuted text-xs">{r.total_responses} responses</span>
              </div>
            ))}
          </div>
        </div>
        <p className="text-textMuted text-xs mt-4">Manage verification status from Django Admin.</p>
      </div>
    </DashboardLayout>
  )
}
