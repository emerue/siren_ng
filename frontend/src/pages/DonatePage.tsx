import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getIncident, initiateDonation } from '../api'
import type { Incident } from '../types'

const FUNDS = [
  { value: 'VICTIM', icon: '🏠', label: 'Victim Relief', desc: 'Direct to the affected family' },
  { value: 'RESPONDER', icon: '👤', label: 'Responder Appreciation', desc: 'Split among responders on scene' },
  { value: 'PLATFORM', icon: '🚨', label: 'Emergency Response Fund', desc: 'Keeps Siren running' },
]
const QUICK_AMOUNTS = [500, 1000, 2500, 5000]

export default function DonatePage() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const defaultFund = searchParams.get('fund') || 'VICTIM'

  const [fund, setFund] = useState(defaultFund)
  const [amount, setAmount] = useState<number | ''>('')
  const [customAmount, setCustomAmount] = useState('')
  const [form, setForm] = useState({ donor_name: '', donor_email: '', donor_phone: '' })

  const { data: incident } = useQuery<Incident>({
    queryKey: ['incident', id],
    queryFn: () => getIncident(id!),
    enabled: !!id,
  })

  const donateMut = useMutation({
    mutationFn: () =>
      initiateDonation({
        incident_id: id,
        amount_naira: amount || parseFloat(customAmount),
        fund_choice: fund,
        ...form,
      }),
    onSuccess: (data) => {
      window.location.href = data.payment_url
    },
  })

  const finalAmount = amount || parseFloat(customAmount) || 0

  return (
    <div className="min-h-screen bg-bg font-sans">
      <div className="bg-primary text-white px-6 py-4">
        <h1 className="font-bold text-lg">Support this Incident</h1>
        {incident && <p className="text-white/80 text-sm">{incident.incident_type} — {incident.zone_name}</p>}
      </div>

      <div className="max-w-lg mx-auto px-4 py-6 space-y-4">
        {/* Fund choice */}
        <div>
          <h3 className="font-semibold text-textPrimary mb-3">Where should your money go?</h3>
          <div className="space-y-2">
            {FUNDS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFund(f.value)}
                className={`w-full flex items-center gap-3 p-4 rounded-xl border text-left transition ${fund === f.value ? 'border-primary bg-red-50' : 'border-border bg-white hover:border-primary'}`}
              >
                <span className="text-2xl">{f.icon}</span>
                <div>
                  <div className="font-medium text-textPrimary text-sm">{f.label}</div>
                  <div className="text-textMuted text-xs">{f.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Amount */}
        <div>
          <h3 className="font-semibold text-textPrimary mb-3">How much?</h3>
          <div className="grid grid-cols-4 gap-2 mb-3">
            {QUICK_AMOUNTS.map((a) => (
              <button
                key={a}
                onClick={() => { setAmount(a); setCustomAmount('') }}
                className={`py-2 rounded-lg text-sm font-semibold border transition ${amount === a ? 'bg-primary text-white border-primary' : 'bg-white text-textBody border-border hover:border-primary'}`}
              >
                ₦{a.toLocaleString()}
              </button>
            ))}
          </div>
          <input
            type="number"
            value={customAmount}
            onChange={(e) => { setCustomAmount(e.target.value); setAmount('') }}
            placeholder="Custom amount (min ₦500)"
            className="w-full border border-border rounded-lg p-3 text-sm"
            min={500}
          />
        </div>

        {/* Donor details */}
        <div>
          <h3 className="font-semibold text-textPrimary mb-3">Your details</h3>
          <input
            value={form.donor_name}
            onChange={(e) => setForm((f) => ({ ...f, donor_name: e.target.value }))}
            placeholder="Name (optional)"
            className="w-full border border-border rounded-lg p-3 text-sm mb-2"
          />
          <input
            type="email"
            value={form.donor_email}
            onChange={(e) => setForm((f) => ({ ...f, donor_email: e.target.value }))}
            placeholder="Email (required for Paystack)"
            className="w-full border border-border rounded-lg p-3 text-sm mb-2"
          />
          <input
            value={form.donor_phone}
            onChange={(e) => setForm((f) => ({ ...f, donor_phone: e.target.value }))}
            placeholder="WhatsApp number for receipt (optional)"
            className="w-full border border-border rounded-lg p-3 text-sm"
          />
        </div>

        {donateMut.isError && (
          <p className="text-primary text-sm">Payment initiation failed. Please try again.</p>
        )}

        <button
          onClick={() => donateMut.mutate()}
          disabled={!finalAmount || finalAmount < 500 || !form.donor_email || donateMut.isPending}
          className="w-full bg-primary text-white py-4 rounded-xl font-bold text-base disabled:opacity-50 hover:bg-red-700 transition"
        >
          {donateMut.isPending ? 'Redirecting...' : `Donate ₦${finalAmount.toLocaleString() || '—'} with Paystack`}
        </button>

        <p className="text-textMuted text-xs text-center">
          Secure payment via Paystack. Siren takes 10% for platform operations.
        </p>
      </div>
    </div>
  )
}
