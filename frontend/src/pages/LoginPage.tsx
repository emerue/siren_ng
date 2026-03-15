import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function LoginPage() {
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const login = useAuthStore((s) => s.login)
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(form)
      navigate('/dashboard')
    } catch {
      setError('Invalid credentials. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg font-sans flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl border border-border p-8 w-full max-w-sm">
        <Link to="/" className="block text-center font-bold text-primary text-xl mb-6">🚨 Siren.ng</Link>
        <h2 className="text-xl font-bold text-textPrimary mb-6 text-center">Dashboard Login</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            value={form.username}
            onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
            placeholder="Username"
            autoComplete="username"
            required
            className="w-full border border-border rounded-lg p-3 text-sm"
          />
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            placeholder="Password"
            autoComplete="current-password"
            required
            className="w-full border border-border rounded-lg p-3 text-sm"
          />
          {error && <p className="text-primary text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-white py-3 rounded-lg font-semibold disabled:opacity-50 hover:bg-red-700 transition"
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className="text-textMuted text-xs text-center mt-4">
          This login is for agency operators and platform admins only.
        </p>
      </div>
    </div>
  )
}
