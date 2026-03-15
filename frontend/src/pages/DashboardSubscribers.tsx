import { useQuery } from '@tanstack/react-query'
import { getAnalyticsSubscribers } from '../api'
import DashboardLayout from '../components/DashboardLayout'

export default function DashboardSubscribers() {
  const { data } = useQuery({
    queryKey: ['analytics-subscribers'],
    queryFn: () => getAnalyticsSubscribers('30d'),
    refetchInterval: 60_000,
  })

  return (
    <DashboardLayout>
      <div className="p-8">
        <h1 className="text-2xl font-bold text-textPrimary mb-6">Location Subscribers</h1>
        {data && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            {[
              { label: 'Active Subscriptions', value: data.active_subscriptions },
              { label: 'Total Alerts Sent', value: data.total_alerts_sent },
              { label: 'Alerts (last 30d)', value: data.alerts_in_range },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-xl border border-border p-5">
                <div className="text-3xl font-bold text-textPrimary">{s.value}</div>
                <div className="text-textMuted text-sm">{s.label}</div>
              </div>
            ))}
          </div>
        )}
        <p className="text-textMuted text-sm">Manage individual subscriptions from Django Admin.</p>
      </div>
    </DashboardLayout>
  )
}
