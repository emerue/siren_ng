import { useQuery } from '@tanstack/react-query'
import { getOrganisationsMap } from '../api'
import DashboardLayout from '../components/DashboardLayout'
import type { Organisation } from '../types'

export default function DashboardOrgs() {
  const { data: orgs = [], isLoading } = useQuery<Organisation[]>({
    queryKey: ['orgs-map'],
    queryFn: getOrganisationsMap,
  })

  return (
    <DashboardLayout>
      <div className="p-8">
        <h1 className="text-2xl font-bold text-textPrimary mb-6">Organisations</h1>
        {isLoading && <p className="text-textMuted">Loading...</p>}
        <div className="bg-white rounded-xl border border-border">
          <div className="px-6 py-4 border-b border-border font-semibold text-textPrimary">Verified Partners</div>
          {orgs.length === 0 && !isLoading && (
            <p className="text-textMuted text-center py-8 text-sm">No verified organisations yet.</p>
          )}
          <div className="divide-y divide-border">
            {orgs.map((org) => (
              <div key={org.id} className="px-6 py-4 flex items-center gap-4">
                <div className="flex-1">
                  <div className="font-medium text-textPrimary text-sm">{org.name}</div>
                  <div className="text-textMuted text-xs">{org.org_type} · {org.zone_name} · {org.operating_hours}</div>
                </div>
                <span className="text-textMuted text-xs">{org.total_responses} responses</span>
              </div>
            ))}
          </div>
        </div>
        <p className="text-textMuted text-xs mt-4">Manage verification from Django Admin.</p>
      </div>
    </DashboardLayout>
  )
}
