# SIREN.NG — BUSINESS REQUIREMENTS DOCUMENT v8.3
**July 2026 · Status: PILOT SPINE BUILT (backend-verified, pending deploy) · FRAMING LOCK PENDING SEGMENT 2**
**Supersedes v7.3 for all strategy, scope, and build decisions. v7.3 is demoted to TECHNICAL ARCHIVE — the as-built record of Phases 1–8 and the parking lot for post-MVP features. Consult it for implementation detail on existing code only. Where v7.3 conflicts with this document, v8 wins.**

---

## 0. HOW TO READ THIS DOCUMENT

This BRD does one job: define the smallest product that tests Siren's riskiest assumption with real Lagosians, and the rules for deciding what happens next. It is deliberately small. Everything Siren might someday be lives in the v7.3 archive, not here.

One section of this document is explicitly PROVISIONAL — the framing of the core value (Section 3). It locks only when the Phase 0 validation sprint closes. Everything else is committed.

---

## 0.1 CURRENT BUILD STATE — v8.2 (July 2026)

At-a-glance status of the pilot spine. Detail lives in §5 (scope) and §14 (change log); this block is the summary. Legend: ✅ built · 🟡 hidden for MVP · 🔴 out/archived · ⏳ outstanding.

### ✅ Added / changed this cycle (v8.2 code, in working tree)
- **Human-confirm gate** — AI now *classifies only* (type/severity/LGA/confidence) and parks every plausible report in the `DETECTED` queue. It no longer auto-verifies and never broadcasts. A coordinator's admin **"Mark VERIFIED"** is the sole trigger for any alert. (§5.1.2, §8)
- **Authority notification** — new `forward_to_authorities` Celery task fires on VERIFIED: structured summary to configured WhatsApp number(s) and/or a webhook, delivery logged, incident advanced to `AGENCY_NOTIFIED`, never surfaced to users as a promise. (§5.1.4)
- **Promise-Invariant copy** — verified message, LGA-subscriber alert, cross-location alert, and resolution message rewritten to state only what Siren did ("your neighbours in <LGA> have been alerted; we have notified emergency services"). Removed "community responder notified / clinic alerted" and all donation/fundraising lines. (§8)
- **WATCH/STOP/LIST** — `LIST` added; multi-LGA `WATCH A, B` split; alias table (VI/Lekki→Eti-Osa, Yaba→Lagos Mainland, …) confirmed. (§6 US-2)
- **English + Pidgin copy** — per-user language preference: default English, sender texts **PIDGIN / ENGLISH** to switch (stored durably on hash-keyed `WhatsAppProfile`), first contact answered bilingually. Core-loop messages (ack, verified, rejected, resolution, LGA alert) have Pidgin variants. (§7 NFR)
- **Feature-flag system** — `settings.FEATURES` (one env switch per feature, defaults = MVP), `utils/features.py`, and `GET /api/features/`; the web nav gates HIDDEN/OUT links by flag. Flip a flag in Railway → Variables + restart to release a feature — no code change. Frontend gating written but not built (npm cert issue).
- **AI provider** — kept switchable via `AI_PROVIDER` (groq↔anthropic); default and logic unchanged.

### 🟡 Hidden for the MVP (in code, off in the flow — may return)
- **Community vouching / `VERIFYING`** — AI no longer routes here; returns at Phase 1.5 when LGA density supports thresholds.
- **Commute Shield** — trigger gated behind `ENABLE_COMMUTE_SHIELD` (default **off**).
- **Guardian Mode web subscriptions, media-gallery polish, My Impact.**

### 🔴 Out / archived (built in v7.3, not in the MVP)
Donations UI + the 10% victim-fund cut (revoked permanently), resource boards, historical-data layer, zone safety scores/rings/drawers, commute briefings, the v7.3 web design system.

### ⏳ Outstanding for full v8 conformance
- **Build the frontend** so the feature-flag gating takes effect (blocked locally by an npm TLS/cert issue; Railway builds it on deploy). Optionally extend gating from nav links to full route guards.
- Pidgin variants for the *secondary* copy (responder/org/onboarding prompts); core loop is done.
- Outside-hours auto-reply + coordinator coverage-hours/escalation (§5.4, §7).
- Gatekeeper onboarding kit — non-code (one-pager + QR + demo script).

### ⚠️ Verification & deployment state (be honest about this)
- **Environment built & verified (July 2026).** Python 3.13 venv created; dependencies installed (with `cbor2<5.5` pinned — see below); `python manage.py check` → **0 issues**; `makemigrations --check` → **no missing migrations**; import + copy smoke test → **passed** (`forward_to_authorities` registered, `verify_incident_ai` confirmed not auto-broadcasting, Promise-Invariant copy asserts clean). Note: the repo ships **no unit tests** (0 collected), so verification is check + smoke-test level, not suite-level.
- **`cbor2` pin added** to `requirements.txt` (`cbor2<5.5`): 5.5+ switched to a Rust build with no py3.13/Intel-mac wheel and breaks `pip install`; the older pure-Python wheel installs cleanly.
- **Committed to branch `v8-pilot-spine`** (3 commits: pilot-spine, feature-flag system, English+Pidgin) — **not yet pushed, not deployed.** Railway still runs pre-v8 code. `main` is untouched.
- New local dev affordance: `DATABASE_URL=sqlite://` now runs the app with no DB server (production postgres path unchanged). Migrations applied and app boots (HTTP 200); one new migration `whatsapp/0001_initial` (WhatsAppProfile).
- Next steps: `git push -u origin v8-pilot-spine` → PR → review → merge to `main` (which triggers the Railway deploy, building the frontend there).

---

## 1. EXECUTIVE SUMMARY

Siren.ng is a WhatsApp-based community emergency platform for Lagos. A resident reports an emergency on WhatsApp; a trusted human verifies it (AI-assisted); subscribed neighbours in that LGA are alerted so the community can respond; the verified report is forwarded to official emergency services; the reporter is told when it's resolved.

The riskiest assumption: **Lagosians will trust and use this instead of defaulting to calling family and handling it themselves.** The MVP exists to test that, in one neighbourhood, distributed through one church and one mosque.

What Siren promises users: *community response and honest information*. What Siren never promises: *that official help will arrive*. This distinction is a hard invariant (Section 8).

---

## 2. THE PROBLEM (verified basis)

- 67.9% of calls to Lagos emergency lines (767/112) were fake or nuisance calls over Jan 2025–Apr 2026; 5.47M genuine calls went unanswered; abandonment rose from 9.3% to 37.6%. (Lagos State data via ministerial briefing, May 2026.)
- Only ~3% of Nigerians call an ambulance first in a medical emergency; 78% call family/friends or self-transport (ERA survey). 44% who reached a hospital were rejected, delayed, or referred untreated; 64% dissatisfied.
- Trust in formal responders is near-zero (6.4% express strong trust in police).
- WhatsApp reaches ~95% of Nigerian internet users; it is the de facto communication infrastructure.
- Bystanders overwhelmingly DO help (93.2% assistance rate, Abuja study) but only ~29% render effective aid — the gap is skill and structure, not willingness.

⚠️ **FLAGGED — resolve before external use:** (1) Top incident category: LASEMA 2025 data suggests road traffic crashes lead (394 RTC + 249 tanker) vs. other sources suggesting fires (1,685). Verify against the primary LASEMA report and update here. (2) Any legacy claim of "53% of calls unanswered" or "68% of bystanders do nothing" is retired — superseded by the figures above.

**The gap in one sentence:** when an emergency happens, Lagosians don't trust the official system, can't get fast help, and rely on word-of-mouth that is fast but unverified. Siren adds verification + structure to the community response that already exists, on the channel people already use.

---

## 3. CORE VALUE FRAMING — ⚠️ PROVISIONAL, VALIDATION-GATED

Working hypothesis (Reading A, adopted June 2026): **community coordination + verified local alerts**, with best-effort official notification. Pitch: *"Report it. Your neighbours are alerted to help, and emergency services are notified."*

### 3.1 INTERIM VALIDATION READOUT — Segment 1 (July 2026, n=19, digital channel, ages 19–29)

- **Fork:** "Get help to actually come" 9/18 · "Confirm family safe" 4 · "What's happening" 3 · "Areas to avoid" 2. Coordination beats pure awareness ~2:1. Open-text unmet needs were all *means of response* (extinguisher, ambulance, car, medical attention, security) — zero asked for information.
- **Feasibility:** official help arrived quickly in **0/18** real incidents (5 slow, 5 never, 8 didn't call). Confirms the promise invariant (§8): community response is the only deliverable promise.
- **Adoption wall:** 14/18 chose "a service that coordinates nearby help" over "handle it myself." Cleared, even discounted for social-desirability bias.
- **Behavior:** 11/17 first actions were family/friend/neighbour; only 3 called 767/112. Matches national self-help data.
- **WTP:** 16/19 above zero (9 pay-per-use, 7 small monthly). Floor exists; per-use leads.
- **⚠️ Trust flag:** faith figures and known neighbours scored zero as trusted alert sources in this segment; official-looking accounts, social media, and apps led. Interpretation pending interviews — likely demographic (young, connected). Consequence: verification voice in alerts must read official ("Confirmed by Siren coordinator"); faith communities remain the *distribution* channel for the older segment. Distribution and trust-voice are separate decisions.
- **Interview pool:** 8 phone numbers volunteered.

**What this authorizes:** building the pilot spine (§5.4) now — every component is required under any surviving framing. **What it does not authorize:** locking the framing, launching alerts publicly, or skipping Segment 2 (on-the-ground, Pidgin, low-income). N=19 from one digital channel is signal, not proof.

This framing locks ONLY when Phase 0 closes. Pre-committed kill criteria (numbers set by the team BEFORE fielding — fill in and never move them):

| Signal | Source | Threshold | If breached |
|---|---|---|---|
| Fork | Survey Q6 (one-thing question) | "What's happening near me" ranked #1 by fewer than ___% | Pure-awareness framing is dead |
| App trust | Survey Q7 grid | "App/automated system: not at all" above ___% | Automated-front product dead; human-front mandatory |
| Feasibility | Survey Q3 + interviews | Official help arrived (at all) in fewer than ___% of real incidents | "Help is coming" language dead; community-only promise |
| Adoption wall | Survey Q8 | "Handle it myself" beats "use a service" | Overrides everything; rethink before building |

Analysis rules: behavior questions (what people actually did) outrank all stated-preference questions when they conflict. Situated scenario (fire-two-streets-away) outranks abstract ranking. N≥50 completed per neighbourhood before any segment claim. Two contrasting neighbourhoods, recruited through different channels (digital vs. on-the-ground).

---

## 4. CUSTOMER & GO-TO-MARKET

**Beachhead: LOCKED — Oshodi-Isolo** (v8.1). Rationale: survey respondents clustered in Isolo/Oshodi/Ajao/Mafoluku; it was already a top candidate; we hold contactable real users there. Entered through ONE church and ONE mosque simultaneously. Faith communities provide, in one place: the most-trusted distribution in Nigeria, a ready pool of willing community responders, and hyperlocal subscriber density.

**Segments (in adoption order):** (1) faith-community members in the pilot neighbourhood — recruited by their pastor/imam's endorsement; (2) estate residents and school parent groups in the same LGA — Phase 2 gatekeepers; (3) market traders/low-connectivity residents — reached via assisted onboarding and (post-MVP) SMS/voice fallback.

**The Lagos mother remains the emotional core customer** but is reached through gatekeepers, never direct ads.

**GTM invariants:** Siren is religiously neutral — it partners with churches AND mosques and is never branded to either. Users subscribe to where they LIVE, not where they worship. The gatekeeper relationship is owned by a named Field/Community Lead.

---

## 5. MVP SCOPE

### 5.1 IN (the core loop — build/verify these only)
1. **Report** — WhatsApp message (text/voice-adjacent text/media) to the Siren number. Multilingual (English, Pidgin, Yoruba, Hausa, Igbo, mixed). Never rejected for brevity or language alone. (Built.)
2. **Verify** — AI classifies (type, severity, LGA) as assist; a **named human coordinator confirms before any broadcast**. Users see human verification ("Confirmed by Siren coordinator"), never "AI verified." Target: median < 10 minutes report-to-verified during pilot hours. (Built — AI now classifies to the DETECTED queue only; broadcast fires solely on admin confirm. See §14 v8.2.)
3. **Alert** — all active subscribers in the incident's LGA receive a WhatsApp template alert (approved business-initiated template; SID held in env `TWILIO_TEMPLATE_ZONE_ALERT`). Subscribe/unsubscribe via WATCH / STOP <LGA> / LIST commands. (Built — WATCH/STOP/LIST wired, multi-LGA `WATCH A, B`, alias table, and per-subscriber English/Pidgin all done.)
4. **Notify authorities** — every verified incident is forwarded to LASEMA/official channels as a best-effort notification. No MoU required or awaited. (Built — `forward_to_authorities` Celery task, WhatsApp + webhook channels, delivery logged, never surfaced to users.)
5. **Close the loop** — reporter receives a WhatsApp resolution message when the incident is marked resolved. (Built; verify end-to-end.)
6. **Tracking page** — public per-incident status page with media. (Built.)

### 5.2 HIDDEN (in code, off in UI, may return)
Guardian Mode web subscriptions; vouching (returns at Phase 1.5 when LGA density supports thresholds — until then, only human-verified incidents alert; nothing waits in community-review limbo); media gallery polish; My Impact.

### 5.3 OUT of MVP (archived in v7.3)
Commute Shield; resource boards; donations UI; historical data layer; zone safety scores; safety-score rings/drawers; commute briefings; Section 21 web design system (revisit when web resurfaces as an acquisition surface).

### 5.4 MISSING — must be specified and built for MVP
- **Human verification workflow:** ✅ BUILT. AI classifies to the DETECTED queue and never broadcasts; only admin confirm fires downstream tasks; alerts read "Confirmed by Siren coordinator." Still to specify (non-code): coverage hours and the outside-hours auto-hold/auto-reply. Displayed coordinator name set to official register ("Siren coordinator").
- **WATCH/STOP/LIST WhatsApp commands:** ✅ BUILT (checked before emergency-intent routing). LIST, multi-LGA `WATCH A, B`, and the alias table (VI/Victoria Island, Lekki → Eti-Osa) all done.
- **LASEMA forward task:** ✅ BUILT. `forward_to_authorities` sends a structured summary to configured WhatsApp numbers and/or a webhook on VERIFIED, logs the delivery attempt, advances the incident to AGENCY_NOTIFIED, and never surfaces delivery status to users.
- **English + Pidgin copy:** ✅ BUILT (§7 NFR). Per-user preference (PIDGIN/ENGLISH commands, durable `WhatsAppProfile`), core-loop messages translated, first-contact bilingual. Secondary copy (responder/org prompts) still English-only.
- **Feature-flag system:** ✅ BUILT. `settings.FEATURES` + `utils/features.py` + `GET /api/features/`; web nav gates by flag. Release an OUT/HIDDEN feature by flipping its env var in Railway and restarting. Frontend build pending (npm cert).
- **Gatekeeper onboarding kit:** ⏳ NOT STARTED (non-code) — one-page explainer + QR + demo script for the pastor/imam; assisted-subscription flow for low-literacy members.

**Also outstanding for full v8 conformance:** build the frontend so flag-gating renders (blocked locally by npm cert; Railway builds on deploy); outside-hours auto-reply + coordinator coverage-hours.

---

## 6. CORE-LOOP USER STORIES & ACCEPTANCE CRITERIA

**US-1 Reporter.** As a resident who witnesses an emergency, I message the Siren number and get an immediate acknowledgment, a verification result, and a resolution message when it's over.
- AC: acknowledgment < 10s; "Fire at Isolo market" (or Pidgin equivalent) creates an incident; verification message includes type + LGA + tracking link; resolution message sent exactly once on RESOLVED.

**US-2 Subscriber.** As a resident, I text WATCH <my LGA> and thereafter receive an alert whenever a verified incident occurs in my LGA, and can STOP anytime.
- AC: "WATCH Surulere" subscribes and confirms; aliases normalize (Yaba→Lagos Mainland, Isolo→Oshodi-Isolo, VI→Eti-Osa, ~20 LGAs + common aliases); "WATCH Surulere, Yaba" subscribes both; "LIST" returns active subscriptions; "STOP Surulere" deactivates and confirms; "STOP" alone defers to the global opt-out keyword; a VERIFIED incident in a subscribed LGA delivers the template alert; "Fire at Surulere market" is never parsed as a command.

**US-3 Coordinator.** As the verification coordinator, I see new reports, confirm or reject each with one action, and my confirmation triggers alerts + LASEMA forward + reporter notification.
- AC: confirm fires `_post_verification_actions`; reject sends the rejection message; every transition writes a ResponseLog entry; no broadcast ever occurs without a human confirm.

**US-4 Gatekeeper.** As a pastor/imam, I can explain Siren in one sentence, my members can join in under a minute (assisted if needed), and I can see it working (verified incidents + resolutions in my area).
- AC: onboarding kit exists; a member with only WhatsApp can subscribe with one message; the gatekeeper receives a simple weekly summary (manual is fine at pilot scale).

---

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Availability:** webhook and alert pipeline target 99% during pilot; any incident-pipeline outage is a P0.
- **Latency:** report acknowledgment <10s; alert fan-out to all LGA subscribers <2 min from human confirm.
- **Verification SLA:** median <10 min during covered hours; outside covered hours, reports queue with an honest auto-reply ("received — a coordinator will confirm shortly").
- **Language:** all user-facing WhatsApp copy available in English and Pidgin at launch. *(Built for the core loop: per-user preference via PIDGIN/ENGLISH, default English, first contact bilingual. Secondary copy still English-only.)*
- **Security invariants (carried from v7.3 §23, unchanged and permanent):** Twilio signature validation before any processing; phone-hash-keyed rate limiting (10/60s), never IP-keyed; non-obvious admin URL; AI prompt sandboxing with USER INPUT delimiters; reporter_phone stored only for delivery (max 30 chars, Twilio `whatsapp:+...` format), never in API responses, INFO logs, or WebSocket payloads; reporter_hash (SHA-256) for all identity lookups.
- **Technical stack corrections (v8 supersedes v7.3 Quick Reference):** Database connects via the **Supabase Transaction pooler (port 6543)** — this is the configuration that stabilized production; do NOT revert to direct 5432. AI verification provider is **Groq** (document the model in env); Anthropic references in v7.3 §10 are historical. IncidentMedia field names are `public_url`, `file_size` (bytes), `upload_timestamp` (v7.3 §17.4 is authoritative; §7.1 model listing is stale). No GeoDjango, no psycopg2, Haversine-with-HAVING — all unchanged.

---

## 8. THE PROMISE INVARIANT (liability line)

**Siren never tells a user that professional help is coming.** Approved language: "Your neighbours in <LGA> have been alerted." / "We have notified emergency services." Banned language anywhere in product, marketing, or templates: "help is on the way," "responders are on their way," "an ambulance has been dispatched," or any equivalent. The v7.3 §21.4 example status copy ("responders are on their way") is revoked. Every alert states what Siren did (alerted, notified), never what third parties will do. This invariant ranks with the security invariants: never weakened, ever.

Companion rule: **only human-verified incidents are ever broadcast.** Speed never overrides verification. An unverified report reaches no one but the coordinator.

---

## 9. SUCCESS METRICS & DECISION GATES

**Pilot success (Phase 1, one neighbourhood, ~6 weeks):**
- ≥30 active subscribers via the two faith communities (≥50 stretch)
- ≥5 genuine incidents reported and human-verified
- ≥60% of surveyed alert recipients report taking an action (avoided area / checked on family / went to help / told someone)
- ≥1 organic referral chain (subscriber who joined via another subscriber, unprompted)
- Both gatekeepers still actively promoting at week 6
- Zero false-alert broadcasts; zero promise-invariant violations

**Kill/pivot signals:** subscribers churn silently after first alert; gatekeepers stop mentioning it; reports arrive but subscribers don't act; verification SLA unmeetable with available people. Any two of these → stop and rediagnose before expanding.

**Instrumentation:** reports/week, verification time, alert delivery success (Twilio status), subscriber count per LGA, resolution count, WATCH/STOP ratio. Manual spreadsheet acceptable at pilot scale; do not build a dashboard for 50 users.

---

## 10. BUSINESS MODEL — HYPOTHESES TO TEST (not commitments)

Siren has no proven revenue model. Candidates, in test order:
1. **Grants** (civic-tech, public-safety, health) — most realistic first money; CAC registration is the gating item. Pursue during Phase 1.
2. **B2B2C community subscriptions** — estates, schools, and faith communities pay a modest fee for verified coverage of their area. Test willingness with pilot gatekeepers in Phase 2.
3. **Verified-data partnerships** (insurers, logistics, eventually government) — only after meaningful incident volume.

**Donations policy (supersedes v7.3 §13):** donations UI is out of MVP. When it returns: victim-relief funds pass through at 100% (platform absorbs processing fees); platform-fund donations may retain 100%; **Siren never takes a percentage of victim or responder funds.** The prior 10% cut is revoked as a reputational risk with no defensible upside.

Survey Q9 (willingness to pay) informs only whether any tolerance exists above zero; it never sets price.

---

## 11. RISKS & MITIGATIONS

| Risk | L | I | Mitigation |
|---|---|---|---|
| Over-promise → death/blame | M | Critical | Promise invariant (§8); coordinator training; copy review on every template |
| False alert broadcast → trust collapse / panic | M | Critical | Human-verify-before-broadcast invariant; one alert per verified incident; misinformation precedent (India WhatsApp lynchings) briefed to all coordinators |
| Validation returns mush; team defaults to what's built | H | High | Pre-committed kill numbers (§3); board review of results before any framing lock |
| Gatekeeper never converts / goes cold | M | High | Two gatekeepers (church + mosque) so one failure isn't fatal; Field Lead owns relationships |
| Meta template rejection / number migration breaks delivery | M | Med | Approved SID banked; template changes tested on sandbox; +234 migration before scale, never after |
| Solo-founder + unpaid team fragility | M | High | Cash contributions logged as company loans; vesting; founders' agreement papered before Phase 2 |
| Twilio/Groq cost spike or balance exhaustion | L | Med | Balance alerts (current balance is low — top up before fielding); per-message cost tracked from pilot day one |
| Coordinator unavailable during incident | M | Med | Coverage-hours honesty (auto-reply), second trained coordinator by week 3 |

---

## 12. ROADMAP

**Phase 0 — Validation sprint (now, 2–3 weeks).** Field the Pidgin+English survey through two channels; 8 behavior-reconstruction interviews; feasibility read (did help come, private-responder calls); apply kill criteria; lock framing. **No new feature code ships in Phase 0** except what the pilot strictly requires and validation doesn't touch (WATCH/STOP/LIST may be built, not launched).
**Gate:** framing locked + kill criteria applied + board sign-off.

**Phase 1 — Single-neighbourhood pilot (4–6 weeks).** Launch through one church + one mosque in one LGA. Build list = §5.4 only. Run success metrics (§9). Weekly user conversations.
**Gate:** pilot success criteria met.

**Phase 2 — Expand + monetize test.** Second/third LGA via new gatekeepers; +234 number acquired, Meta-verified, migrated; first paid-gatekeeper conversation; vouching returns if density supports; SMS/USSD fallback scoped for low-connectivity segment.

**Explicitly not scheduled:** LASEMA MoU (parallel side-quest, never blocking), fundraising (only after Phase 1 traction), any v7.3 archived feature.

---

## 13. TEAM & GOVERNANCE (summary — details in founders' agreement)

Roles: Technical Owner (founder), Field/Community Lead (gatekeepers, onboarding, responders), Ops & Trust Lead (verification, false-alarm management, support). Community responders are congregation volunteers, not hires. All cash contributions are documented loans to the company until the equity split is set — which happens **after** Phase 0 closes, not before. All equity vests.

---

## 14. CHANGE LOG — v7.3 → v8

- v7.3 demoted to technical archive; v8 is the single source of truth for scope and strategy.
- Strategy inverted: WhatsApp-first (was web-first); coordination+verified-alerts framing, validation-gated (was awareness/Guardian hero); gatekeeper GTM via faith communities (was none).
- Verification: human-front, AI-assist (was AI-front).
- Promise invariant added; "responders on their way" copy revoked.
- Donations: out of MVP; 10% victim-fund cut revoked permanently.
- Problem stats corrected; two flagged for primary-source resolution.
- Stack corrections: pooler 6543 documented as production truth; Groq documented as verification provider; IncidentMedia field names reconciled.
- Success metrics, kill criteria, risk register, business-model hypotheses, user stories, and acceptance criteria added (all absent from v7.3).
- Phases renumbered around validation (0) → pilot (1) → expansion (2); v7.3's Phases 1–8 stand as the as-built record.

**v8 → v8.1 (July 2026):** Interim Segment-1 readout added (§3.1) — coordination leads 2:1, feasibility 0/18 fast official response, adoption wall cleared, WTP floor above zero, trust-voice flag raised. Pilot LGA locked: Oshodi-Isolo. Pilot-spine build (§5.4) authorized ahead of framing lock; framing lock still gated on Segment 2 + interviews. Verification voice set to official-register ("Confirmed by Siren coordinator").

**v8.1 → v8.2 (July 2026) — pilot-spine build landed.** Evidence: §5.4 pilot-spine authorization (v8.1) + the human-verified-only broadcast rule (§8). Code changes:
- **Human-confirm gate enforced** — `verify_incident_ai` now only classifies (type/severity/LGA/confidence) and leaves the report in DETECTED. It no longer auto-verifies, no longer routes to VERIFYING/vouching (HIDDEN, §5.2), and never calls `_post_verification_actions`. Broadcast fires only on admin "Mark VERIFIED." Satisfies §5.1.2 and the §8 companion rule.
- **LASEMA notification** — `forward_to_authorities` added and wired into `_post_verification_actions` (§5.1.4).
- **Promise Invariant applied** — verified message, LGA subscriber alert, cross-location alert, and resolution copy rewritten to state only what Siren did ("your neighbours in <LGA> have been alerted; we have notified emergency services"); "community responder notified / clinic alerted" and all donation/fundraising lines removed (§8, §5.3).
- **Commute Shield disabled** — gated behind `ENABLE_COMMUTE_SHIELD` (default off), per §5.3.
- **WATCH/STOP/LIST** — `LIST` command added alongside `MY ALERTS`.
- **AI provider** — left switchable via `AI_PROVIDER` (groq↔anthropic), unchanged per instruction.
- Still open: multi-LGA WATCH + alias table, ConnectPage copy fix, `settings.py`/`.env.example` declarations for `LASEMA_FORWARD_NUMBERS`/`LASEMA_FORWARD_WEBHOOK`/`ENABLE_COMMUTE_SHIELD`, Pidgin copy, hiding OUT/HIDDEN web features, gatekeeper kit.
- Added §0.1 CURRENT BUILD STATE as the at-a-glance summary of this build. Verification/deployment caveat recorded there: changes are local-only, not committed, not deployed, and not yet runtime-verified (local env unbuildable on Python 3.14).

**v8.2 → v8.3 (July 2026) — bilingual + feature flags.** Evidence: §7 NFR (English + Pidgin at launch) and the operational need to release OUT/HIDDEN features one at a time (§5.2/5.3). Committed on branch `v8-pilot-spine`:
- **English + Pidgin** — per-user language preference (PIDGIN/ENGLISH commands; durable hash-keyed `WhatsAppProfile`; migration `whatsapp/0001_initial`). Core-loop copy (ack, verified, rejected, resolution, LGA alert) translated; first contact bilingual. Reporter/subscriber tasks look up language per recipient. Resolved-notification donation line removed (§5.3).
- **Feature-flag system** — `settings.FEATURES` (one env switch per feature, defaults = MVP), `utils/features.py`, `GET /api/features/`; web nav gates HIDDEN/OUT links by flag. Release/hide a feature by flipping its env var in Railway and restarting — no code change. `ENABLE_COMMUTE_SHIELD` folded in as `FEATURES["commute_shield"]`.
- **WATCH** — multi-LGA `WATCH A, B` split completed; alias table (VI/Lekki→Eti-Osa) confirmed.
- **Local dev** — `DATABASE_URL=sqlite://` now runs the app with no DB server (production postgres path unchanged); `cbor2<5.5` pinned.
- Verified: `manage.py check` 0 issues, migrations apply, app boots (HTTP 200), smoke tests pass. Not yet pushed/deployed; `main` untouched. Frontend flag-gating written but unbuilt (npm cert).

*Update this document only through the change log. Every framing change must cite the evidence that forced it.*
