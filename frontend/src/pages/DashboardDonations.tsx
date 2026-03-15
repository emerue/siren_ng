import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAnalyticsDonations } from '../api'
import DashboardLayout from '../components/DashboardLayout'

export default function DashboardDonations() {
  const [range, setRange] = useState('30d')

  const { data } = useQuery({
    queryKey: ['analytics-donations', range],
    queryFn: () => getAnalyticsDonations(range),
    refetchInterval: 60_000,
  })

  return (
    <DashboardLayout>
      <div className="p-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-textPrimary">Donations</h1>
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

        {data && (
          <>
            <div className="bg-white rounded-xl border border-border p-6 mb-6">
              <div className="text-4xl font-bold text-textPrimary">₦{(data.total_naira || 0).toLocaleString()}</div>
              <div className="text-textMuted mt-1">Total raised in selected period</div>
            </div>

            <div className="bg-white rounded-xl border border-border p-6">
              <h3 className="font-semibold text-textPrimary mb-4">By Fund</h3>
              <div className="space-y-3">
                {(data.per_fund || []).map((f: { fund: string; naira: number }) => (
                  <div key={f.fund} className="flex justify-between items-center">
                    <span className="text-textBody text-sm">{f.fund}</span>
                    <span className="font-semibold text-textPrimary">₦{f.naira.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        <p className="text-textMuted text-xs mt-4">View individual donations in Django Admin → Donation.</p>
      </div>
    </DashboardLayout>
  )
}
