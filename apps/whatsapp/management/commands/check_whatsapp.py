"""
Pre-flight readiness check for the WhatsApp sender.

Answers one question before you point production at a number:
"can this sender actually deliver alerts to real subscribers?"

    python manage.py check_whatsapp
    python manage.py check_whatsapp --number +15559907768

Read-only: it sends no messages and changes no configuration. Uses the Twilio
REST API directly rather than the SDK so it does not break across SDK versions.
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand

API = "https://api.twilio.com/2010-04-01"
MESSAGING = "https://messaging.twilio.com/v2"
CONTENT = "https://content.twilio.com/v1"

OK, WARN, BAD = "PASS", "WARN", "FAIL"


class Command(BaseCommand):
    help = "Check whether the WhatsApp sender is ready to deliver alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--number",
            help="Sender to check, e.g. +15559907768. Defaults to TWILIO_WHATSAPP_NUMBER.",
        )

    def handle(self, *args, **opts):
        sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        target = (opts.get("number") or getattr(settings, "TWILIO_WHATSAPP_NUMBER", "") or "")
        target = target.replace("whatsapp:", "").strip()

        if not sid or not token:
            self.stderr.write(self.style.ERROR(
                "TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN are not set in this environment."))
            return

        auth = (sid, token)
        results = []

        self.stdout.write(self.style.MIGRATE_HEADING("\nWhatsApp sender readiness\n"))

        # 1. Credentials + account state ----------------------------------
        try:
            r = requests.get(f"{API}/Accounts/{sid}.json", auth=auth, timeout=20)
            if r.status_code == 401:
                results.append((BAD, "Credentials", "Rejected by Twilio (401). Check SID/token."))
                return self._report(results)
            r.raise_for_status()
            acct = r.json()
            state = acct.get("status", "unknown")
            results.append((
                OK if state == "active" else BAD,
                "Credentials / account",
                f"{acct.get('friendly_name','?')} — status: {state}",
            ))
        except Exception as exc:
            results.append((BAD, "Credentials", f"Could not reach Twilio: {exc}"))
            return self._report(results)

        # 2. Balance -------------------------------------------------------
        try:
            r = requests.get(f"{API}/Accounts/{sid}/Balance.json", auth=auth, timeout=20)
            bal = float(r.json().get("balance", 0))
            cur = r.json().get("currency", "USD")
            # A pilot fan-out costs real money per message; a near-empty
            # balance stops delivery mid-incident.
            results.append((
                OK if bal >= 20 else WARN,
                "Account balance",
                f"{bal:.2f} {cur}" + ("" if bal >= 20 else "  ← top up before fielding"),
            ))
        except Exception as exc:
            results.append((WARN, "Account balance", f"Could not read: {exc}"))

        # 3. WhatsApp senders ---------------------------------------------
        found = None
        try:
            r = requests.get(f"{MESSAGING}/Channels/Senders", auth=auth, timeout=25)
            if r.status_code == 200:
                senders = r.json().get("senders", []) or []
                if not senders:
                    results.append((BAD, "WhatsApp senders", "No WhatsApp senders on this account."))
                for s in senders:
                    num = str(s.get("sender_id", "")).replace("whatsapp:", "")
                    status = s.get("status", "unknown")
                    is_target = target and num.endswith(target.lstrip("+")[-9:])
                    if is_target:
                        found = (num, status, s)
                    results.append((
                        OK if status.upper() == "ONLINE" else WARN,
                        f"Sender {num}" + ("  ← target" if is_target else ""),
                        f"status: {status}",
                    ))
            else:
                results.append((WARN, "WhatsApp senders",
                                f"Could not list (HTTP {r.status_code}). Check in the Console."))
        except Exception as exc:
            results.append((WARN, "WhatsApp senders", f"Could not list: {exc}"))

        if target:
            if found and str(found[1]).upper() == "ONLINE":
                results.append((OK, "Target number", f"{target} is registered and ONLINE"))
            elif found:
                results.append((BAD, "Target number", f"{target} exists but status is {found[1]}"))
            else:
                results.append((BAD, "Target number",
                                f"{target} is not a registered WhatsApp sender on this account"))

        # 4. Approved templates -------------------------------------------
        configured = getattr(settings, "TWILIO_TEMPLATE_ZONE_ALERT", "")
        try:
            r = requests.get(f"{CONTENT}/ContentAndApprovals", auth=auth, timeout=25)
            if r.status_code == 200:
                items = r.json().get("contents", []) or []
                approved = []
                for c in items:
                    ap = (c.get("approval_requests") or {})
                    status = ap.get("status", "unknown")
                    if status == "approved":
                        approved.append((c.get("sid"), c.get("friendly_name")))
                if approved:
                    for csid, name in approved[:10]:
                        results.append((OK, "Approved template", f"{csid}  {name or ''}"))
                else:
                    results.append((BAD, "Approved templates",
                                    "None approved. LGA alerts are business-initiated and "
                                    "will be rejected outside the 24h window."))
                if configured:
                    match = [c for c, _ in approved if c == configured]
                    results.append((
                        OK if match else BAD,
                        "TWILIO_TEMPLATE_ZONE_ALERT",
                        f"{configured} " + ("is approved" if match else "is NOT in the approved list"),
                    ))
                else:
                    results.append((BAD, "TWILIO_TEMPLATE_ZONE_ALERT",
                                    "Not set — alerts fall back to free-form text"))
            else:
                results.append((WARN, "Templates", f"Could not list (HTTP {r.status_code})."))
        except Exception as exc:
            results.append((WARN, "Templates", f"Could not list: {exc}"))

        self._report(results)

    def _report(self, results):
        width = max(len(label) for _, label, _ in results) + 2
        for level, label, detail in results:
            style = {OK: self.style.SUCCESS, WARN: self.style.WARNING, BAD: self.style.ERROR}[level]
            self.stdout.write(f"  {style(level.ljust(4))}  {label.ljust(width)} {detail}")

        fails = [r for r in results if r[0] == BAD]
        warns = [r for r in results if r[0] == WARN]
        self.stdout.write("")
        if fails:
            self.stdout.write(self.style.ERROR(
                f"NOT READY — {len(fails)} blocking issue(s). "
                "Do not point production at this number yet."))
        elif warns:
            self.stdout.write(self.style.WARNING(
                f"READY WITH WARNINGS — {len(warns)} item(s) to watch."))
        else:
            self.stdout.write(self.style.SUCCESS(
                "READY — sender is online and an approved template is configured."))
        self.stdout.write("")
