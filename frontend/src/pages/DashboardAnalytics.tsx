import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { getAnalyticsSummary, getAnalyticsTrends, getAnalyticsZones, getAnalyticsDonations } from '../api'
import DashboardLayout from '../components/DashboardLayout'

export default function DashboardAnalytics() {
  const [range, setRange] = useState('7d')

  const { data: summary } = useQuery({ queryKey: ['analytics-summary', range], queryFn: () => getAnalyticsSummary(range) })
  const { data: trends } = useQuery({ queryKey: ['analytics-trends', range], queryFn: () => getAnalyticsTrends(range) })
  const { data: zones } = useQuery({ queryKey: ['analytics-zones', range], queryFn: () => getAnalyticsZones(range) })
  const { data: donations } = useQuery({ queryKey: ['analytics-donations', range], queryFn: () => getAnalyticsDonations(range) })

  return (
    <DashboardLayout>
      <div className="p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-textPrimary">Analytics</h1>
          <div className="flex gap-2">
            {['7d', '30d', '90d'].map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold border transition ${range === r ? 'bg-primary text-white border-primary' : 'bg-white text-textBody border-border hover:border-primary'}`}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        {/* Summary cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Active Incidents', value: summary.active_incidents },
              { label: "Today's Total", value: summary.today_total },
              { label: 'Responders Available', value: summary.responders_available },
              { label: 'Total Donated Today', value: `₦${(summary.total_donated_today_naira || 0).toLocaleString()}` },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-xl border border-border p-5">
                <div className="text-2xl font-bold text-textPrimary">{s.value}</div>
                <div className="text-textMuted text-sm">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Trends */}
          {trends && trends.length > 0 && (
            <div className="bg-white rounded-xl border border-border p-5">
              <h3 className="font-semibold mb-4 text-textPrimary">Daily Incidents</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E8" />
                  <XAxis dataKey="day" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#C0392B" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Zones */}
          {zones && zones.length > 0 && (
            <div className="bg-white rounded-xl border border-border p-5">
              <h3 className="font-semibold mb-4 text-textPrimary">Incidents by Zone</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={zones.slice(0, 8)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E8E8E8" />
                  <XAxis dataKey="zone_name" tick={{ fontSize: 9 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#C0392B" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Donations */}
          {donations && (
            <div className="bg-white rounded-xl border border-border p-5">
              <h3 className="font-semibold mb-2 text-textPrimary">Donations</h3>
              <div className="text-3xl font-bold text-textPrimary mb-3">
                ₦{(donations.total_naira || 0).toLocaleString()}
              </div>
              <div className="space-y-2">
                {(donations.per_fund || []).map((f: { fund: string; naira: number }) => (
                  <div key={f.fund} className="flex justify-between text-sm">
                    <span className="text-textBody">{f.fund}</span>
                    <span className="font-medium text-textPrimary">₦{f.naira.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  )
}
