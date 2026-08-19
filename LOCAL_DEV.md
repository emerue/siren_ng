# Running Siren.ng locally

Every command here was run and verified on this machine (macOS, Intel).

**Which setup do you want?**

| | Terminals | Use when |
|---|---|---|
| **A. One terminal** | 1 | You just want to click through the app. Build the UI once, Django serves everything on `:8000`. No live reload. |
| **B. Two terminals** | 2 | You are editing frontend code and want hot reload. |

### A. One terminal (simplest)

```bash
cd "/Users/user/Desktop/coding project/Siren/siren_ng"
source .venv/bin/activate
(cd frontend && npm run build)      # only after frontend changes
python manage.py runserver 8000
```

Open <http://127.0.0.1:8000>. Django serves the built UI *and* the API from one
port (verified: assets return real JS, not the SPA fallback). Re-run the build
whenever you change frontend code.

### B. Two terminals (frontend development)

Both servers run at once; each holds its terminal until you press `Ctrl+C`.
Use two tabs (`Cmd+T`) or VS Code's split terminal.

---

## 0. One-time prerequisites

### Python 3.13 — not 3.14

The project targets 3.13. On **3.14 the install fails**: `cbor2` (pulled in via
`daphne` → `autobahn`) builds from Rust source on 3.14 and there is no wheel.

```bash
brew install python@3.13
```

### Node

Node 20+ works (verified on Node 26).

---

## 1. Backend (Django)

```bash
cd "/Users/user/Desktop/coding project/Siren/siren_ng"

# Create the venv on 3.13 (already done once — skip unless rebuilding)
/Users/user/homebrew/opt/python@3.13/bin/python3.13 -m venv .venv

source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins `cbor2==5.9.0`, which ships a pure-Python wheel — it
needs no Rust toolchain and carries the current security fixes.

### Environment

A local `.env` already exists (gitignored). It points at **SQLite** so you need
no database server:

```
DATABASE_URL=sqlite:///db.sqlite3
CELERY_ALWAYS_EAGER=True
AI_PROVIDER=groq          # switchable: groq | anthropic
```

`settings.py` only forces the Postgres backend for `postgres://` URLs, so
production is unaffected by this.

### Migrate and run

```bash
python manage.py migrate
python manage.py createsuperuser     # needed for the verification queue
python manage.py runserver 8000
```

Check it: <http://127.0.0.1:8000/api/features/> should return the feature-flag JSON.

---

## 2. Frontend (React + Vite)

### First install — two known gotchas

```bash
cd "/Users/user/Desktop/coding project/Siren/siren_ng/frontend"
```

**(a) TLS / certificate error.** If `npm install` fails with
`UNABLE_TO_GET_ISSUER_CERT_LOCALLY`, something on the network (VPN/antivirus)
is inspecting HTTPS and Node does not trust its root. Export the macOS trust
store once and point Node at it — this keeps certificate verification **on**
(do not use `strict-ssl false`):

```bash
mkdir -p ~/.certs
security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > ~/.certs/roots.pem
security find-certificate -a -p /Library/Keychains/System.keychain >> ~/.certs/roots.pem

# add to ~/.zshrc to make it permanent
export NODE_EXTRA_CA_CERTS=~/.certs/roots.pem
```

**(b) Peer-dependency conflict.** `react-leaflet@4.2.1` wants React 18 but the
project is on React 19, so plain `npm install` aborts:

```bash
npm install --legacy-peer-deps
```

> Proper fix (not yet done): upgrade to `react-leaflet@^5`, which supports
> React 19. Then `--legacy-peer-deps` is no longer needed.

### Run it

```bash
npm run dev          # http://localhost:5173
```

`vite.config.ts` proxies `/api` and `/ws` to `http://127.0.0.1:8000`, so the UI
talks to Django with no CORS setup and no rebuild. Point it elsewhere with
`VITE_DEV_API_TARGET`.

Set the WhatsApp number used by the CTAs (optional):

```bash
echo 'VITE_WHATSAPP_NUMBER=+234XXXXXXXXXX' >> .env.local
```

### Production build

```bash
npm run build        # tsc -b && vite build → dist/
npm run preview      # serves dist/ on :4173, same proxy
```

Django's SPA view serves `frontend/dist/index.html`, so after a build the app is
also available on :8000.

---

## 3. Testing the v8 core loop

The human-verification gate is the heart of v8: **AI never broadcasts.**

1. A report arrives (WhatsApp webhook, or create an Incident in the admin).
2. `verify_incident_ai` classifies it and leaves it in **DETECTED**.
3. Go to <http://127.0.0.1:8000/admin/> → Incidents → select → **"Mark selected
   as VERIFIED"**. Only this fires alerts, the LASEMA forward and the reporter
   notification.
4. The public page at `/track/<id>` shows each step that actually happened.

### Feature flags

Everything HIDDEN/OUT in the v8 MVP is off by default. To try one, set it in
`.env` and restart Django:

```
FEATURE_DONATIONS=True
FEATURE_GUARDIAN_WEB=True
ENABLE_COMMUTE_SHIELD=True
```

Current state is always visible at `/api/features/`, and the web UI follows it.

### Full async flows (optional)

`CELERY_ALWAYS_EAGER=True` runs tasks inline, which is enough for most testing.
For the real queue:

```bash
brew install redis && redis-server                 # terminal 3
celery -A sirenapp worker -l info                  # terminal 4
```

Real WhatsApp delivery additionally needs valid Twilio credentials and a public
webhook URL (e.g. ngrok).

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `No module named 'django'` | venv not activated → `source .venv/bin/activate` |
| `Failed building wheel for cbor2` | Running Python 3.14, or pip chose the sdist → use 3.13 and `pip install --only-binary cbor2 cbor2==5.9.0` |
| `connection to server on socket /tmp/.s.PGSQL.5432 failed` | `DATABASE_URL` points at Postgres; use `sqlite:///db.sqlite3` locally |
| `UNABLE_TO_GET_ISSUER_CERT_LOCALLY` | Set `NODE_EXTRA_CA_CERTS` (§2a) |
| `ERESOLVE could not resolve` on npm install | Use `--legacy-peer-deps` (§2b) |
| `That port is already in use` | `lsof -ti:8000 \| xargs kill` |
| Frontend loads but API calls 404 | Django not running on :8000, or you opened :4173/:5173 without the proxy |
