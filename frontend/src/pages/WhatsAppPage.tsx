import { Link } from 'react-router-dom'

const WHATSAPP_NUMBER = import.meta.env.VITE_WHATSAPP_NUMBER || '+2349000000000'
const WA = WHATSAPP_NUMBER.replace('+', '')

const COMMANDS = [
  { cmd: 'Emergency at [location]', desc: 'Report an emergency instantly', color: 'text-red-700 bg-red-50 border-red-200' },
  { cmd: 'WATCH [location name]', desc: 'Subscribe to alerts for a location', color: 'text-blue-700 bg-blue-50 border-blue-200' },
  { cmd: 'COMMUTE [home] to [office]', desc: 'Get daily commute safety briefings', color: 'text-indigo-700 bg-indigo-50 border-indigo-200' },
  { cmd: 'RESPONDER', desc: 'Join as a community first responder', color: 'text-green-700 bg-green-50 border-green-200' },
  { cmd: 'REGISTER ORG', desc: 'Register your organisation', color: 'text-purple-700 bg-purple-50 border-purple-200' },
  { cmd: 'MY ALERTS', desc: 'View all your active subscriptions', color: 'text-amber-700 bg-amber-50 border-amber-200' },
  { cmd: 'VOUCH [incident-id]', desc: 'Confirm an incident is real', color: 'text-teal-700 bg-teal-50 border-teal-200' },
  { cmd: 'STOP [label]', desc: 'Unsubscribe from a location alert', color: 'text-gray-700 bg-gray-50 border-gray-200' },
]

const ALERTS = [
  { icon: '🔥', text: 'Fires, floods, road accidents, collapses near you' },
  { icon: '⚡', text: 'Electrical hazards and infrastructure alerts' },
  { icon: '🚗', text: 'Commute route safety briefings (morning + evening)' },
  { icon: '✅', text: 'When incidents near you are resolved' },
  { icon: '🆘', text: 'Critical alerts for your family locations' },
  { icon: '📊', text: 'Daily zone safety score for your neighbourhood' },
]

export default function WhatsAppPage() {
  return (
    <div className="min-h-screen bg-bg font-sans">
      {/* Nav */}
      <nav className="bg-white border-b border-border px-6 py-4 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold text-primary">🚨 Siren.ng</Link>
        <div className="flex gap-4 text-sm">
          <Link to="/feed" className="text-textBody hover:text-primary">Feed</Link>
          <Link to="/report" className="text-textBody hover:text-primary">Report</Link>
          <Link to="/watch" className="text-textBody hover:text-primary">Watch</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="bg-gradient-to-br from-green-700 to-green-900 text-white py-20 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/15 rounded-full px-4 py-2 text-sm mb-6 border border-white/20">
            <span className="text-xl">📱</span>
            Works on any phone with WhatsApp · No app needed
          </div>
          <h1 className="text-4xl font-bold mb-4 leading-tight">
            Get emergency alerts<br />on WhatsApp
          </h1>
          <p className="text-white/85 text-lg mb-8 max-w-md mx-auto leading-relaxed">
            Save our number, send one message, and you're enrolled. Receive real-time alerts for emergencies near your home, office, and commute route.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href={`https://wa.me/${WA}?text=Hello`}
              className="flex items-center justify-center gap-2 bg-white text-green-800 font-bold px-8 py-3.5 rounded-xl hover:bg-green-50 transition shadow-lg"
            >
              <span className="text-xl">💬</span> Open WhatsApp Chat
            </a>
            <button
              onClick={() => navigator.clipboard.writeText(WHATSAPP_NUMBER)}
              className="flex items-center justify-center gap-2 border-2 border-white/50 text-white font-semibold px-8 py-3.5 rounded-xl hover:bg-white/10 transition"
            >
              <span>📋</span> Copy Number
            </button>
          </div>
          <p className="text-white/60 text-sm mt-4 font-mono">{WHATSAPP_NUMBER}</p>
        </div>
      </section>

      {/* How to register */}
      <section className="py-16 px-6 max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-textPrimary mb-2 text-center">How to register in 3 steps</h2>
        <p className="text-textMuted text-center mb-10">No forms, no account, no app download required.</p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              step: '1',
              icon: '💾',
              title: 'Save the number',
              desc: `Save ${WHATSAPP_NUMBER} as a contact on your phone. Name it "Siren NG" or whatever works for you.`,
              cta: null,
            },
            {
              step: '2',
              icon: '💬',
              title: 'Send your first message',
              desc: 'Open WhatsApp and send "WATCH [your area]" — for example: "WATCH Lekki Phase 1".',
              cta: { label: 'Send WATCH now', href: `https://wa.me/${WA}?text=WATCH%20My%20Location` },
            },
            {
              step: '3',
              icon: '✅',
              title: 'You\'re enrolled',
              desc: 'Siren will confirm your subscription and start sending you alerts when emergencies are reported near that location.',
              cta: null,
            },
          ].map((item) => (
            <div key={item.step} className="bg-white rounded-2xl border border-border p-6 relative">
              <div className="absolute -top-3 -left-3 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center text-sm font-bold shadow">
                {item.step}
              </div>
              <div className="text-4xl mb-4 mt-2">{item.icon}</div>
              <h3 className="font-bold text-textPrimary mb-2">{item.title}</h3>
              <p className="text-textBody text-sm leading-relaxed">{item.desc}</p>
              {item.cta && (
                <a
                  href={item.cta.href}
                  className="mt-4 inline-flex items-center gap-1 text-green-700 font-semibold text-sm hover:underline"
                >
                  {item.cta.label} →
                </a>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* What you'll receive */}
      <section className="py-12 px-6 bg-green-50 border-y border-green-100">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-textPrimary mb-2 text-center">What you'll receive</h2>
          <p className="text-textMuted text-center mb-8">Alerts are AI-verified before they reach you — no spam, no false alarms.</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {ALERTS.map((a) => (
              <div key={a.text} className="flex items-start gap-3 bg-white rounded-xl border border-green-100 p-4">
                <span className="text-2xl shrink-0">{a.icon}</span>
                <span className="text-sm text-textBody leading-relaxed">{a.text}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Commands */}
      <section className="py-16 px-6 max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-textPrimary mb-2 text-center">Available commands</h2>
        <p className="text-textMuted text-center mb-8">Send any of these to Siren on WhatsApp.</p>
        <div className="space-y-3">
          {COMMANDS.map((c) => (
            <a
              key={c.cmd}
              href={`https://wa.me/${WA}?text=${encodeURIComponent(c.cmd)}`}
              className="flex items-center gap-4 bg-white rounded-xl border border-border p-4 hover:shadow-sm hover:border-green-300 transition group"
            >
              <code className={`text-sm font-mono font-bold px-3 py-1.5 rounded-lg border ${c.color} shrink-0`}>
                {c.cmd}
              </code>
              <span className="text-sm text-textBody flex-1">{c.desc}</span>
              <span className="text-green-600 opacity-0 group-hover:opacity-100 transition text-sm font-semibold shrink-0">Send →</span>
            </a>
          ))}
        </div>
      </section>

      {/* Report section */}
      <section className="py-12 px-6 bg-white border-t border-border">
        <div className="max-w-3xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
            <div>
              <h2 className="text-2xl font-bold text-textPrimary mb-3">Reporting emergencies via WhatsApp</h2>
              <p className="text-textBody text-sm leading-relaxed mb-4">
                Just describe what you see in plain language. No special format needed. Siren's AI will extract the type, location, and severity automatically.
              </p>
              <div className="space-y-2 mb-4">
                {[
                  '"There is a building on fire at 5 Akin Adesola, VI"',
                  '"Major accident on Third Mainland Bridge, 3 vehicles involved"',
                  '"Flood water rising fast in Surulere, Lawanson area"',
                ].map((ex) => (
                  <div key={ex} className="bg-gray-50 rounded-lg px-4 py-2 text-sm text-textBody italic border border-border">
                    {ex}
                  </div>
                ))}
              </div>
              <p className="text-xs text-textMuted">You can also attach a photo or video directly in WhatsApp.</p>
            </div>
            <div className="bg-green-50 rounded-2xl border border-green-100 p-6 text-center">
              <p className="text-5xl mb-4">🚨</p>
              <p className="font-bold text-textPrimary mb-2">In an emergency?</p>
              <p className="text-textBody text-sm mb-5">Don't type commands — just describe what's happening and where.</p>
              <a
                href={`https://wa.me/${WA}?text=Emergency`}
                className="block bg-green-700 text-white font-bold px-6 py-3 rounded-xl hover:bg-green-800 transition"
              >
                Open WhatsApp to report →
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-14 px-6 max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold text-textPrimary mb-8 text-center">Common questions</h2>
        <div className="space-y-4">
          {[
            ['Do I need to create an account?', 'No. Your WhatsApp number is your identity. We never ask for a password, email, or name.'],
            ['Is my number stored?', 'We store only a one-way hash of your number — we can send you messages but cannot reverse it back to your phone number.'],
            ['How many locations can I watch?', 'Up to 5 active POINT subscriptions plus 1 COMMUTE route per number.'],
            ['Can I stop alerts?', 'Yes — send "STOP [label]" to unsubscribe from any location, or "STOP ALL" to unsubscribe from everything.'],
            ['What if I send a false report?', 'Our AI detects false reports automatically. Repeated false reports result in your number being blocked from reporting.'],
          ].map(([q, a]) => (
            <details key={q} className="bg-white border border-border rounded-xl group">
              <summary className="p-4 font-semibold text-textPrimary cursor-pointer list-none flex items-center justify-between">
                {q}
                <span className="text-textMuted group-open:rotate-180 transition-transform">▾</span>
              </summary>
              <div className="px-4 pb-4 text-sm text-textBody leading-relaxed">{a}</div>
            </details>
          ))}
        </div>
      </section>

      {/* Footer CTA */}
      <section className="py-10 px-6 bg-green-700 text-white text-center">
        <p className="text-lg font-bold mb-2">Start receiving alerts now</p>
        <p className="text-white/80 text-sm mb-5">It takes 30 seconds. No forms required.</p>
        <a
          href={`https://wa.me/${WA}?text=WATCH%20My%20Location`}
          className="inline-flex items-center gap-2 bg-white text-green-800 font-bold px-8 py-3 rounded-xl hover:bg-green-50 transition"
        >
          <span>💬</span> Start on WhatsApp
        </a>
      </section>
    </div>
  )
}
