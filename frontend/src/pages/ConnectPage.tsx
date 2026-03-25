import Nav from '../components/Nav'
import { Link } from 'react-router-dom'

const WHATSAPP_NUMBER = import.meta.env.VITE_WHATSAPP_NUMBER || '+2349000000000'
const WA = WHATSAPP_NUMBER.replace('+', '')

const COMMANDS = [
  { cmd: 'CONNECT',      desc: 'First-time setup and NDPR consent' },
  { cmd: 'WATCH',        desc: 'Start location subscription flow' },
  { cmd: 'MY ALERTS',    desc: 'List all active saved locations and radii' },
  { cmd: 'STOP [label]', desc: 'Pause alerts for a specific location' },
  { cmd: 'STOP ALL',     desc: 'Opt out of all Siren messages permanently' },
  { cmd: 'MY COMMUTE',   desc: "Check today's commute route status" },
  { cmd: 'POINT',        desc: 'Save as single Guardian point' },
  { cmd: 'COMMUTE',      desc: 'Set up Commute Shield (Home + Office corridor)' },
  { cmd: 'NEED RIDE',    desc: 'Connect with people offering transport near incident' },
  { cmd: 'MY IMPACT',    desc: 'Get link to your impact page' },
  { cmd: 'RESPONDER',    desc: 'Register as a community responder' },
  { cmd: 'REGISTER ORG', desc: 'Register organisation as verified partner' },
  { cmd: 'VOUCH [id]',   desc: 'Vouch for an incident' },
  { cmd: 'YES / NO',     desc: 'Accept or decline a responder dispatch' },
  { cmd: 'ONSCENE',      desc: 'Confirm arrival at scene' },
  { cmd: 'DONE',         desc: 'Confirm response complete' },
  { cmd: 'HELP',         desc: 'Show the full command list' },
]

const STEPS = [
  { n: '1', icon: '💬', title: 'Send CONNECT', desc: 'Tap the button below or open WhatsApp and send CONNECT to our number. We\'ll walk you through a quick one-time setup.' },
  { n: '2', icon: '📍', title: 'Save your locations', desc: 'Send WATCH and follow the prompts. Add your home, your children\'s school, your office — any location you care about.' },
  { n: '3', icon: '🛡️', title: 'We monitor in real time', desc: 'Our system watches for verified emergencies within your chosen radius, 24/7, without draining your battery.' },
  { n: '4', icon: '🔔', title: 'You get an instant alert', desc: 'The moment a verified threat is detected near any saved location, we send you a WhatsApp message with full details and a tracking link.' },
]

const PRIVACY = [
  { icon: '🔐', text: 'Your number is stored as a one-way cryptographic hash — we cannot reverse it.' },
  { icon: '🚫', text: 'Your number is never sold, shared, or used for marketing.' },
  { icon: '📜', text: 'Fully compliant with Nigeria\'s NDPR data protection regulation.' },
  { icon: '✋', text: 'Reply STOP at any time to permanently opt out. No questions asked.' },
]

export default function ConnectPage() {
  return (
    <div className="min-h-screen bg-bg font-sans">
      <Nav />

      {/* Hero — above the fold */}
      <section className="bg-gradient-to-br from-green-700 via-green-800 to-green-900 text-white py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/15 border border-white/20 rounded-full px-4 py-1.5 text-sm mb-6">
            <span className="w-2 h-2 bg-green-300 rounded-full animate-pulse"></span>
            <span className="font-medium">WhatsApp Integration · Free · No app download</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold mb-5 leading-tight">
            Get Siren alerts directly<br />on WhatsApp
          </h1>
          <p className="text-white/85 text-lg mb-10 max-w-xl mx-auto leading-relaxed">
            Connect once. Get notified instantly when emergencies happen near your saved locations.
          </p>
          <a
            href={`https://wa.me/${WA}?text=CONNECT`}
            className="inline-flex items-center gap-3 bg-white text-green-800 font-bold px-10 py-4 rounded-2xl hover:bg-green-50 transition shadow-xl text-lg"
          >
            <span className="text-2xl">💬</span> Connect WhatsApp
          </a>
          <p className="text-white/50 text-xs mt-5">
            Your number is never shared. Opt out anytime by replying STOP.
          </p>
        </div>
      </section>

      {/* What you get */}
      <section className="py-16 px-6 max-w-5xl mx-auto">
        <h2 className="text-2xl font-bold text-center text-textPrimary mb-10">What you get on WhatsApp</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white border-2 border-green-200 rounded-2xl p-8 hover:shadow-md transition">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center text-2xl mb-5">🔔</div>
            <h3 className="text-xl font-bold text-textPrimary mb-3">Instant incident alerts</h3>
            <p className="text-textBody leading-relaxed">
              Get notified the moment a verified emergency happens within your chosen radius of any saved location. Name your locations — "Home", "Bola's School", "Mum's house" — and we watch them all.
            </p>
          </div>
          <div className="bg-white border-2 border-green-200 rounded-2xl p-8 hover:shadow-md transition">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center text-2xl mb-5">📣</div>
            <h3 className="text-xl font-bold text-textPrimary mb-3">Quick reporting from the field</h3>
            <p className="text-textBody leading-relaxed">
              If you witness an emergency, send a WhatsApp message and we handle the rest. No app, no form, no account. Our AI verifies it in under 90 seconds and routes it to the right responders.
            </p>
          </div>
        </div>
      </section>

      {/* How reporting works */}
      <section className="py-14 px-6 bg-white border-y border-border">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center text-textPrimary mb-12">How emergency reporting works</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {STEPS.map((s) => (
              <div key={s.n} className="text-center">
                <div className="w-10 h-10 bg-green-600 text-white rounded-full flex items-center justify-center text-sm font-bold mx-auto mb-4">
                  {s.n}
                </div>
                <div className="text-4xl mb-3">{s.icon}</div>
                <h3 className="font-semibold text-textPrimary mb-2 text-sm">{s.title}</h3>
                <p className="text-textBody text-xs leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Sample chat bubble */}
      <section className="py-16 px-6 max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold text-center text-textPrimary mb-10">See it in action</h2>
        <div className="space-y-4">
          {/* User bubble */}
          <div className="flex justify-end">
            <div className="bg-green-100 text-green-900 rounded-2xl rounded-tr-sm px-5 py-3.5 max-w-xs shadow-sm">
              <p className="text-sm leading-relaxed">Fire! Smoke from 3rd floor 14 Adewale Street Surulere</p>
              <p className="text-[10px] text-green-600 mt-1.5 text-right">You · just now</p>
            </div>
          </div>
          {/* Siren bubble */}
          <div className="flex justify-start">
            <div className="flex items-start gap-2.5">
              <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center text-sm shrink-0 mt-0.5">🚨</div>
              <div className="bg-white border border-border rounded-2xl rounded-tl-sm px-5 py-3.5 max-w-xs shadow-sm">
                <p className="text-xs font-bold text-green-700 mb-1">Siren.ng</p>
                <p className="text-sm leading-relaxed text-textPrimary">
                  <span className="font-bold text-green-700">VERIFIED</span> — Fire incident, Surulere. Responders dispatched.<br />
                  <span className="text-blue-600 underline text-xs">Track: siren.ng/track/abc123</span>
                </p>
                <p className="text-[10px] text-textMuted mt-1.5">Siren.ng · ~90 seconds ago</p>
              </div>
            </div>
          </div>
        </div>
        <p className="text-center text-textMuted text-xs mt-6">
          That's all it takes. No forms, no account, no app download.
        </p>
      </section>

      {/* Commands reference */}
      <section className="py-14 px-6 bg-white border-y border-border">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center text-textPrimary mb-3">WhatsApp commands reference</h2>
          <p className="text-center text-textBody text-sm mb-10">Send any of these to our WhatsApp number to get started.</p>
          <div className="overflow-hidden rounded-2xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-green-50 text-left">
                  <th className="px-5 py-3 font-semibold text-green-800 text-xs uppercase tracking-wide w-40">Command</th>
                  <th className="px-5 py-3 font-semibold text-green-800 text-xs uppercase tracking-wide">What it does</th>
                </tr>
              </thead>
              <tbody>
                {COMMANDS.map((row, i) => (
                  <tr key={row.cmd} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-5 py-3 font-mono font-semibold text-green-700 text-xs">{row.cmd}</td>
                    <td className="px-5 py-3 text-textBody">{row.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Privacy */}
      <section className="py-14 px-6 max-w-4xl mx-auto">
        <h2 className="text-2xl font-bold text-center text-textPrimary mb-3">Your privacy is protected</h2>
        <p className="text-center text-textBody text-sm mb-10">We built Siren.ng with privacy by design, not as an afterthought.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {PRIVACY.map((item) => (
            <div key={item.text} className="flex items-start gap-4 bg-white border border-border rounded-2xl p-5">
              <span className="text-2xl shrink-0">{item.icon}</span>
              <p className="text-textBody text-sm leading-relaxed">{item.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-14 px-6 bg-green-700 text-white">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to stay informed?</h2>
          <p className="text-white/80 mb-8 leading-relaxed">
            Join thousands of Lagos residents who get instant emergency alerts for the places they care about.
          </p>
          <a
            href={`https://wa.me/${WA}?text=CONNECT`}
            className="inline-flex items-center gap-3 bg-white text-green-800 font-bold px-10 py-4 rounded-2xl hover:bg-green-50 transition shadow-lg text-lg"
          >
            <span className="text-2xl">💬</span> Connect WhatsApp Now
          </a>
          <p className="text-white/50 text-xs mt-4">Free forever · No account · Works on any phone with WhatsApp</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-10 px-6">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-2 font-bold text-lg">
            <span>🚨</span> Siren.ng
          </div>
          <div className="flex flex-wrap justify-center gap-5 text-gray-400">
            <Link to="/"     className="hover:text-white transition">Home</Link>
            <Link to="/feed" className="hover:text-white transition">Feed</Link>
            <Link to="/map"  className="hover:text-white transition">Live Map</Link>
            <Link to="/watch" className="hover:text-white transition">Watch</Link>
            <Link to="/report" className="hover:text-white transition">Report</Link>
            <Link to="/login" className="hover:text-white transition">Admin</Link>
          </div>
          <p className="text-gray-500 text-xs text-center">For Lagos. By the community.</p>
        </div>
      </footer>
    </div>
  )
}
