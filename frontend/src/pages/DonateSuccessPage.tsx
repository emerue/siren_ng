import { useSearchParams, Link } from 'react-router-dom'

export default function DonateSuccessPage() {
  const [params] = useSearchParams()
  const ref = params.get('ref')

  return (
    <div className="min-h-screen bg-bg font-sans flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl border border-border p-8 max-w-md w-full text-center">
        <div className="text-5xl mb-4">✅</div>
        <h1 className="text-2xl font-bold text-textPrimary mb-2">Thank you!</h1>
        <p className="text-textBody mb-6">
          Your donation has been received and will be directed to the fund you chose.
        </p>
        {ref && (
          <p className="text-textMuted text-xs mb-4">Reference: {ref}</p>
        )}
        <div className="space-y-2">
          <button
            onClick={() => navigator.clipboard.writeText(window.location.origin + '/feed')}
            className="w-full border border-border py-3 rounded-lg text-sm hover:border-primary"
          >
            🔗 Share Siren with others
          </button>
          <Link
            to="/"
            className="block w-full bg-primary text-white py-3 rounded-lg text-sm font-semibold hover:bg-red-700 transition"
          >
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  )
}
