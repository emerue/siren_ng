# Issue log

Findings from the architecture review of 12–13 October 2026, against `main` @ `5c33b13`.

**Status values:** `open` · `in progress` · `fixed` · `wontfix` (record why).
**Verified** means the behaviour was confirmed by reading the code paths named in the entry.
Nothing here was reproduced against a running server unless the entry says so.

Severity tiers:

- **P1 — live defect.** Wrong behaviour reaching a user today.
- **P2 — latent risk.** Correct today, but one ordinary change away from failing.
- **P3 — architectural debt.** No current misbehaviour; makes change and testing expensive.

---

## P1 — live defects

### SIREN-001 · `zone-history` 500s on the zone-name path
`open` · verified

`apps/incidents/views.py:418` references `Q` with nothing in scope. Module level imports only
`Count` (`:5`); the three `from django.db.models import Q` statements sit inside conditional
blocks (`:81`, `:85`, `:407`), and `:418` is in the `else` branch of the `:407` one.

`GET /api/incidents/zone-history/?zone_name=Ikeja` raises `NameError: name 'Q' is not defined`
→ 500. Reachable from the UI: `frontend/src/components/ZoneHistoryPanel.tsx:70` takes exactly
this branch whenever coordinates are absent. The `lat`/`lng` branch happens to import `Q` at
`:407` and works, which is why this has not been noticed.

**Fix:** move the import to module level. See SIREN-013 for why this class of bug is possible here.

---

### SIREN-002 · `LIST` / `MY ALERTS` reads a different model from `WATCH`
`open` · verified

`WATCH <lga>` creates `LGASubscription` (`apps/whatsapp/handlers.py:463`).
`show_subscriptions`, reached by `LIST` and `MY ALERTS` (`:92` → `:728`), queries
`LocationSubscription` (`:733`).

A Subscriber who has just subscribed is told they have no saved locations. BRD §6 US-2 lists
`LIST` as core-loop acceptance criteria, so this is in scope for the pilot.

**Fix:** point `show_subscriptions` at `LGASubscription`. Note `handle_stop_command` (`:752`)
reads the same wrong model, but `STOP <lga>` reaches it only as a fallback from
`handle_unsubscribe_command` (`:504`), which uses `LGASubscription` correctly.

---

### SIREN-003 · `Somolu` and `Shomolu` normalise to two different LGAs, so alerts miss subscribers
`open` · verified

Three LGA vocabularies disagree:

| Source | Says |
|---|---|
| `apps/subscriptions/tasks.py:173-174` | `'somolu' → 'Somolu'`, `'shomolu' → 'Shomolu'` — two canonical values |
| `apps/whatsapp/handlers.py:405` | lists both `'Shomolu'` and `'Somolu'` as separate watchable LGAs |
| `apps/incidents/tasks.py:149` | AI prompt collapses `Somolu, Shomolu, Bariga, Ilaje, Pedro → "Shomolu"` |

Both sides of the match run through `normalize_lga_name` — `WATCH` on the user's term
(`handlers.py:455`), the alert on `incident.zone_name` (`subscriptions/tasks.py:31`) — so a
resident who texted `WATCH Somolu` is stored as `'Somolu'` and is **not** matched when the AI
classifies an incident into `'Shomolu'`.

A verified emergency silently fails to reach those neighbours, and the log line reads
`no subscribers for LGA 'Shomolu'`, which looks benign.

**Fix:** one canonical LGA vocabulary, owned by one module, with the AI prompt table, the
watchable list and the normaliser all reading from it.

---

### SIREN-004 · The Promise-Invariant test asserts over a function production never calls
`open` · verified

`tests/test_security.py:357-375` (`PromiseInvariantTests.test_core_loop_copy_is_clean`) checks
`tmpl.resolution_closure(incident, lang)`. Nothing in production calls it.

The copy that actually ships is inlined elsewhere and is outside the check:

- resolution message — `apps/whatsapp/tasks.py:211-227`
- LGA alert, the highest-volume message in the product — `apps/subscriptions/tasks.py:60-83`

The Promise Invariant is BRD §8, the liability line. It is currently unverified on every string
a user actually receives. See SIREN-011.

---

### SIREN-005 · Pidgin speakers get English for the handler strings
`open` · verified (pattern confirmed; line list from the review walk)

`apps/whatsapp/handlers.py` carries roughly 24 inline outbound strings — reported at `126-130,
179, 198, 233, 328, 344, 350, 356-358, 420-427, 477-495, 520-522, 582, 647, 659, 672-674, 681,
724, 745, 781-784, 811, 870-872, 931-933, 955-958` — none of which consult the user's language
preference. A user who has sent `PIDGIN` still gets English for all of them.

The core-loop copy (ack, verified, rejected, more-info) *is* bilingual, so this affects command
replies and edge cases rather than the main loop.

---

### SIREN-006 · Three incompatible phone-identity derivations
`open` · verified

`utils/ratelimit.py:25-50` normalises to E.164 *before* hashing, and documents why (`:8-12`:
trivial reformatting produced different keys and reset the quota). `tests/test_security.py:254-267`
proves it works. **Nothing in the message pipeline calls it.**

- `apps/whatsapp/handlers.py` hashes the raw `from_number` at ten sites: `139, 227, 547, 687,
  732, 750, 816, 860, 905, 917`
- `apps/whatsapp/models.py:26-27` — `WhatsAppProfile.hash_number`, also raw
- `apps/incidents/views.py:34-37` — `_session_hash`, a third scheme (IP + User-Agent + pk)

The same resident messaging as `+2348011112222` and then `08011112222` is two different people
to language preference, subscription listing and `STOP`, and one person to the rate limiter.
`reporter_hash` on the Incident row cannot be joined to the limiter's identity at all.

**Fix:** route every identity derivation through `utils.ratelimit.phone_hash`.

---

### SIREN-007 · Vouch endpoint is public, ungated and loses counts
`open` · verified

`apps/incidents/views.py:129-144`:

- `@permission_classes([AllowAny])`, no `feature_enabled` check, no `hit_rate_limit` — despite
  `FEATURE_VOUCHING` defaulting off
- dedups on `sha256(IP + User-Agent + pk)`, defeated by a new browser profile or a proxy hop
- `incident.vouch_count += 1; save(update_fields=[...])` is read-modify-write, so concurrent
  vouches lose counts — should be `F("vouch_count") + 1`

`apps/whatsapp/handlers.py:174-217` is a second write path with a *disjoint* dedup key
(`sha256(from_number + incident.id)`), so one person can vouch once per channel. It also resolves
incidents by 8-character ID prefix under `.first()` (`:189-191`) and swallows every failure
(`:214-215`, `except Exception: pass`).

Neither path has any test. `frontend/src/pages/FeedPage.tsx:161` still renders the button.

**Design intent to hold it to:** vouches come from people who received the alert, read as a
social-media "like" with a visible count, and speed the coordinator up — they never auto-verify.

---

### SIREN-008 · Feature flags gate nothing
`open` · verified

`utils/features.py:16` — `feature_enabled()` has zero callers anywhere in the codebase. Of 15
flags, one gates backend behaviour and it does so via a back-compat alias rather than the module
(`settings.py:265` → `apps/incidents/tasks.py:276`); one gates an admin template fragment
(`apps/incidents/admin.py:264`, reaching past the module to the dict directly).

Consequences:

- Every HIDDEN and OUT feature answers in production: `apps/resources/views.py` (4 × `AllowAny`),
  `apps/responders/views.py` (6 × `AllowAny`), the vouch endpoint, donation initiate/verify
- Celery beat ignores the flags entirely (`settings.py:317-343`): `daily-safety-score`,
  `morning-commute-briefing`, `evening-commute-briefing` run with `commute_shield: False`, and
  `donation-cleanup` runs with `donations: False`
- The frontend reads 2 of 15 flags (`Nav.tsx:34`, `TrackPage.tsx:292`), while `App.tsx:73-78`
  keeps `/donate/:id`, `/my-impact` and `/guardian` routed

`tests/test_security.py:392-407` asserts the flags are *reported* correctly and default off.
Nothing asserts that an off flag suppresses anything.

**Note:** the donation UI and the 10% victim-fund cut are recorded in the BRD as revoked
permanently, which makes the live `donate/` endpoints the sharpest instance of this.

---

### SIREN-009 · Commute-alert copy hardcodes the host
`open` · verified

`apps/subscriptions/tasks.py:301` emits `siren.ng/track/{id}` and `:409` emits `siren.ng/map`,
while the equivalent template (`apps/whatsapp/templates.py:428-443`) and the LGA alert
(`subscriptions/tasks.py:56`) use `SITE_URL`. `SITE_URL` defaults to `http://localhost:8000`
(`settings.py:165`), so the two renderings disagree in every environment.

Low reach — both are commute-shield paths, an archived feature — but it ships the wrong link if
that feature is ever turned on. Folded into SIREN-011.

---

## P2 — latent risks

### SIREN-010 · A scheduled task can auto-verify and broadcast with no human
`open` · verified

`apps/incidents/coordinator.py:9-11` states the invariant: *"`confirm_and_alert` is the ONLY
function that calls `_post_verification_actions`… There is no time-based or automatic path."*

`apps/incidents/tasks.py:495-500` is exactly that path — actor `'community'`, full fan-out — and
it is wired into beat unconditionally at `settings.py:335-338` (`crontab(minute="*/5")`).

Dormant only because nothing live writes `VERIFYING` (`tasks.py:196`). Two ways to re-arm it:
`apps/incidents/management/commands/import_incidents_csv.py:25` whitelists `"VERIFYING"` in
`VALID_STATUSES`, and `_tasks_patch.py:154` restores the AI → `VERIFYING` route. Either one turns
the public vouch endpoint (SIREN-007) into a broadcast trigger within five minutes, and with
`CRITICAL` needing one vouch (`models.py:108`) that is a single anonymous POST.

`tests/test_coordinator.py:308-327` proves the *SLA* sweep never verifies. There is no equivalent
for this task.

**Fix:** delete `check_verifying_escalation` and its beat entry — the deletion test says no
complexity reappears anywhere. Then pin the invariant with a test asserting that the callers of
`_post_verification_actions` are exactly `{confirm_and_alert}`.

---

### SIREN-011 · REST lifecycle views bypass the coordinator preconditions
`open` · verified

`apps/incidents/views.py:147-167` (`incident_dispatch`, `incident_resolve`) import the private
`_transition` from `apps.incidents.tasks` inside the function body and advance the Incident
directly. Against `coordinator.resolve` (`coordinator.py:164-180`) this path drops:

- the `can_resolve` precondition (`coordinator.py:96`) — so a `DETECTED` or `REJECTED` Incident
  can be resolved straight to a reporter "your report has been resolved" message
- `select_for_update`, the `transaction.atomic` wrapper, `update_fields`
- the `return False` idempotency contract
- the `on_commit` deferral that exists so a worker cannot dequeue pre-commit (`:134-135`)

`incident_dispatch` will push `AGENCY_NOTIFIED` from any status. Both are reachable from the
dashboard via `frontend/src/api/index.ts:38-42`.

`tests/test_security.py:199-203` asserts only `status_code == 200`. The whole
`tests/test_coordinator.py:142-230` suite tests `coordinator.py` and so proves nothing about
this path.

**Fix:** make the two views adapters over `coordinator.resolve` / `coordinator.dispatch`.

---

## P3 — architectural debt

### SIREN-012 · Outbound copy has four implementations
`open` · verified

`apps/whatsapp/templates.py:1-3` claims every outbound message passes through it. Four modules
disagree: `subscriptions/tasks.py:60-83` (LGA alert), `subscriptions/tasks.py:288-302` (near-verbatim
duplicate of `templates.py:428-443`), `whatsapp/tasks.py:211-227` (resolution), and ~24 inline
strings in `handlers.py`.

Five functions in `templates.py` have zero production callers: `subscription_alert:224`,
`resource_board_summary:282`, `commute_setup_office_prompt:412`, `guardian_closure:446`,
`resolution_closure:136`.

Deletion test fails today — the copy is already duplicated, so deleting the module concentrates
nothing. Deepened (every outbound string, keyed by name and language, behind one interface) it
would carry the Promise Invariant for the whole product and make one parametrised test cover
every string in both languages.

Subsumes SIREN-004, SIREN-005, SIREN-009.

---

### SIREN-013 · `zone_history` is 175 lines with no module around it
`open` · verified

`apps/incidents/views.py:329-503` holds a 38-entry `ZONE_CENTROIDS` literal (`:347-386`),
nearest-zone selection by squared degrees (`:387-389`), a raw-SQL haversine via
`connection.cursor()` (`:392-404`), a Python-side average over a `[:500]` slice (`:440-449`), a
12-vs-24-month trend classifier (`:451-461`), and uncommented scoring constants (`:463-488`,
e.g. `freq_penalty = min(70, per_year_eff * 8)`, `lagos_zone_share = round(generic_lagos_count / 20)`).

Zero tests, zero adapters. Largest untested surface in the backend after `handlers.py`, and the
reason SIREN-001 was possible.

---

### SIREN-014 · `route_inbound` is a 20-branch ladder with a dead state machine behind it
`open` · verified

`apps/whatsapp/handlers.py:64-133` dispatches 20 commands as a flat `if` ladder ordered by
accretion. `STOP` is parsed three times over (`:97` → `:498` → reconstructs the string at `:528`
→ re-splits at `:741`).

Unreachable: `start_subscription_flow` (`:601`) has zero callers, and it is the only entry to the
`watch` onboarding state, so `_handle_watch_step` (`:641-725`), `LOCATION_TYPE_MAP` (`:631`),
`RADIUS_MAP` (`:636`) and the `POINT`/`COMMUTE` branch (`:769-795`) cannot be reached from a cold
start. `is_onboarding` at `:117` is therefore always false.

Blanket `except Exception` at `:311` and `:361` converts any bug in the responder replies
(`YES/NO/ONSCENE/DONE/HELP`, `ACCEPT/DECLINE/CALL`) into silence.

2 of 20 commands are tested. Behind a command table (`pattern → handler`, handlers returning a
decided result rather than sending), each becomes one row in a parametrised test.

---

### SIREN-015 · `frontend/src/api/index.ts` is 40 pass-through wrappers around the part that matters
`open` · verified

Lines `3-11` (axios instance + bearer interceptor) earn their keep; `23-147` are
`export const getX = (id) => api.get(...).then(r => r.data)` — each adds a name, removes the
ability to pass per-call options, and adds no error handling, retry, 401 recovery or typing
(`Record<string, unknown>` at `:44, 73, 89, 101, 111`).

The interceptor is bypassed where it counts: `pages/GuardianModePage.tsx:43-75` uses raw `fetch`
against its own `const API = import.meta.env.VITE_API_BASE_URL || ''` (`:5`) with hand-rolled
`authHeaders` (`:33-36`). `DashboardResponders.tsx:2` imports the default `api` and calls it ad hoc.

`refreshToken` (`:153-154`) has zero callers, and `authStore.ts:34-36` exposes a setter nothing
invokes, so the dashboard session dies silently when the access token expires.

No frontend test infrastructure exists — no `*.test.*` under `frontend/src`, no test script in
`frontend/package.json`.

---

### SIREN-016 · Domain policy lives in `settings.py`
`open` · verified

343 lines, 13 touches in the last 60 commits — the highest-churn file in the repo. It carries
coverage hours, coordinator SLA minutes, alert routing, AI provider choice, template SIDs and
media caps. 13 modules read `settings.*` directly for 20 distinct keys
(`services/media_service.py` 11 reads, `apps/incidents/tasks.py` 10).

`utils/coverage.py` is the precedent worth copying: a small module that owns its own config reads
and exposes one question.

---

### SIREN-017 · `_tasks_patch.py` is a rival design sitting in the repo root
`open` · verified

Not a stale duplicate of `apps/incidents/tasks.py` but an alternative that *removes*
`_validate_ai_result`, `_clamp_unit`, the `VALID_INCIDENT_TYPES` / `VALID_SEVERITIES` allowlists,
the AI `timeout=30`, the `--- USER INPUT ---` prompt fencing and the `description[:2000]` bound —
and restores the AI → `VERIFYING` route (`:154`) that SIREN-010 depends on.

So the repo holds two incompatible answers to "is model output trusted?" and "who sets
VERIFYING?", and reading either file alone tells you the wrong thing. Its ~50 lines of
`LANGUAGE_INSTRUCTIONS` / `BREVITY_INSTRUCTIONS` prompt text are the only content worth salvaging.

Also loose in the tree, untracked: `_apply_patches.txt`, `commands.txt`,
`production_ready_script.txt`.

---

### SIREN-018 · Six orphaned Django templates
`open` · verified

`apps/frontend/templates/frontend/{base,home,feed,report,track,track_home}.html` have no caller.
`apps/frontend/views.py` holds only `health`, `_public_config`, `site_config`, `feature_flags`
and `spa`; `apps/frontend/urls.py` is an SPA catch-all. Anyone looking for where a page is
rendered finds two plausible answers and one correct one.

---

### SIREN-019 · The AI prompt is welded into the task body
`open` · verified

`apps/incidents/tasks.py:97-161` inlines a 65-line prompt literal including a 21-line
neighbourhood → LGA table (`:138-160`). No test can vary the prompt or assert on the LGA mapping
without an AI call — and that table is one of the three disagreeing vocabularies in SIREN-003.

---

## Pattern worth naming

The same shape recurs: the pure helper exists and is tested; the bug lives in the call site.

| Helper | Tested at | What the test cannot see |
|---|---|---|
| `utils/ratelimit.py:48` `phone_hash` | `test_security.py:254-267` | 11 call sites hash raw (SIREN-006) |
| `templates.py:136` `resolution_closure` | `test_security.py:372` | production inlines its own copy (SIREN-004) |
| `incidents/tasks.py:285` `_is_safe_authority_url` | `test_security.py:341-346` | applied to the webhook at `:365`, but WhatsApp forwards at `:354-359` are unchecked |
| `incidents/views.py:259` `_is_safe_media_url` | `test_security.py:234-246` | reaches `media_urls` only; `IncidentMedia.public_url` (`views.py:205-212`) is never validated |
| `incidents/tasks.py:31` `_validate_ai_result` | `test_security.py:146-158` | `zone_name` is post-processed at `:174-178`, after validation |
| `subscriptions/tasks.py:152` `normalize_lga_name` | — untested — | three disagreeing vocabularies (SIREN-003) |

Verification concentrates in the helper; change and bugs concentrate in the callers.
