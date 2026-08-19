"""
End-to-end test of the v8 MVP core loop (BRD §5.1).

    Report → AI sorts (DETECTED) → coordinator confirms → LGA neighbours
    alerted + authorities notified + reporter told → resolution closes loop.

Only two boundaries are mocked: the AI provider HTTP call and the Twilio
send. Everything in between — routing, classification, the human gate, LGA
matching, language selection, dedup — runs for real.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.incidents.models import Incident
from apps.incidents.admin import IncidentAdmin
from apps.subscriptions.models import LGASubscription, LGASubscriptionAlert

User = get_user_model()

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

AI_REPLY = {
    "eligible": True,
    "incident_type": "FIRE",
    "severity": "HIGH",
    "ai_confidence": 0.95,
    "fraud_score": 0.02,
    "is_infrastructure": False,
    "zone_name": "Oshodi-Isolo",
    "rejection_reason": "",
}


@override_settings(ALLOWED_HOSTS=["*"], CACHES=LOCMEM, CELERY_TASK_ALWAYS_EAGER=True)
class MvpCoreLoopTests(TestCase):
    REPORTER = "+2348011112222"

    def setUp(self):
        cache.clear()
        self.sent = []          # (to_number, message)
        # Three residents watching Oshodi-Isolo; one watching a different LGA;
        # one unsubscribed. Only the first three may ever be alerted.
        self.subscribers = []
        for i, (lga, active) in enumerate([
            ("Oshodi-Isolo", True),
            ("Oshodi-Isolo", True),
            ("Oshodi-Isolo", True),
            ("Surulere", True),
            ("Oshodi-Isolo", False),
        ]):
            user = User.objects.create_user(f"resident{i}", password="x")
            self.subscribers.append(LGASubscription.objects.create(
                user=user, lga=lga, is_active=active,
                whatsapp_number=f"+23480000000{i:02d}",
            ))

    def _capture_send(self):
        """Patch the single Twilio egress point and record every message."""
        def fake_send(to_number, message):
            self.sent.append((to_number, message))
        m = patch("apps.whatsapp.tasks.send_whatsapp_text.delay", side_effect=fake_send)
        return m

    def _messages_to(self, number):
        return [msg for to, msg in self.sent if number.lstrip("+") in to.lstrip("whatsapp:").lstrip("+")]

    def test_full_core_loop(self):
        from apps.whatsapp.handlers import route_inbound

        with self._capture_send(), \
             patch("apps.incidents.tasks._call_ai", return_value=dict(AI_REPLY)), \
             patch("apps.incidents.tasks.forward_to_authorities.delay") as authority:

            # ── 1. Resident reports on WhatsApp ────────────────────────────
            route_inbound(self.REPORTER, "Fire for Isolo market, near the bus stop", [], None)

            incident = Incident.objects.get()
            self.assertEqual(incident.source, "WHATSAPP")

            # Reporter got an immediate acknowledgment (US-1).
            self.assertTrue(self._messages_to(self.REPORTER),
                            "reporter received no acknowledgment")

            # ── 2. AI sorts but must NOT broadcast ────────────────────────
            incident.refresh_from_db()
            self.assertEqual(incident.status, "DETECTED",
                             "AI must leave the report awaiting a coordinator")
            self.assertEqual(incident.incident_type, "FIRE")
            self.assertEqual(incident.zone_name, "Oshodi-Isolo")

            alerts_before = len([1 for to, _ in self.sent
                                 if "800000000" in to])
            self.assertEqual(alerts_before, 0,
                             "subscribers were alerted BEFORE human confirmation")
            authority.assert_not_called()

            # ── 3. Coordinator confirms in the admin ──────────────────────
            admin = IncidentAdmin(Incident, AdminSite())
            admin.mark_verified(None, Incident.objects.filter(pk=incident.pk))

            incident.refresh_from_db()
            self.assertIn(incident.status, ("VERIFIED", "AGENCY_NOTIFIED"))

            # ── 4. Every active subscriber in THIS LGA is alerted ─────────
            for sub in self.subscribers[:3]:
                msgs = self._messages_to(sub.whatsapp_number)
                self.assertEqual(len(msgs), 1,
                                 f"{sub.whatsapp_number} ({sub.lga}) got {len(msgs)} alerts, expected 1")
                self.assertIn("Oshodi-Isolo", msgs[0])

            # ── 5. Nobody outside the LGA, and no inactive subscriber ─────
            self.assertEqual(self._messages_to(self.subscribers[3].whatsapp_number), [],
                             "subscriber in a DIFFERENT LGA was alerted")
            self.assertEqual(self._messages_to(self.subscribers[4].whatsapp_number), [],
                             "UNSUBSCRIBED user was alerted")

            # ── 6. Authorities notified, reporter told ────────────────────
            authority.assert_called_once()
            reporter_msgs = " ".join(self._messages_to(self.REPORTER))
            self.assertIn("coordinator", reporter_msgs.lower(),
                          "reporter was not told a human confirmed it")

            # ── 7. Promise invariant across every message actually sent ───
            for _, msg in self.sent:
                low = msg.lower()
                for banned in ("on the way", "on their way", "dispatched",
                               "help is coming"):
                    self.assertNotIn(banned, low, f"promise invariant broken: {msg}")

    def test_alert_is_not_sent_twice_for_same_incident(self):
        """Re-running the fan-out must not double-alert (dedup tracker)."""
        from apps.subscriptions.tasks import notify_location_subscribers

        incident = Incident.objects.create(
            source="WHATSAPP", reporter_hash="h" * 64, reporter_phone=self.REPORTER,
            description="Fire", incident_type="FIRE", severity="HIGH",
            status="VERIFIED", zone_name="Oshodi-Isolo",
        )
        with self._capture_send():
            notify_location_subscribers(str(incident.id))
            first = len(self.sent)
            notify_location_subscribers(str(incident.id))
            second = len(self.sent)

        self.assertEqual(first, 3, f"expected 3 alerts, got {first}")
        self.assertEqual(second, first, "duplicate alerts sent on re-run")
        self.assertEqual(LGASubscriptionAlert.objects.count(), 3)

    def test_watch_then_receive_alert(self):
        """US-2: a resident texts WATCH <LGA> and is alerted next incident."""
        from apps.whatsapp.handlers import route_inbound
        from apps.subscriptions.tasks import notify_location_subscribers

        newcomer = "+2348099998888"
        with self._capture_send():
            route_inbound(newcomer, "WATCH Oshodi-Isolo", [], None)

        sub = LGASubscription.objects.filter(lga="Oshodi-Isolo",
                                             whatsapp_number__contains="99998888").first()
        self.assertIsNotNone(sub, "WATCH did not create a subscription")
        self.assertTrue(sub.is_active)

        incident = Incident.objects.create(
            source="WHATSAPP", reporter_hash="h" * 64, description="Flood",
            incident_type="FLOOD", severity="MEDIUM", status="VERIFIED",
            zone_name="Oshodi-Isolo",
        )
        self.sent = []
        with self._capture_send():
            notify_location_subscribers(str(incident.id))

        self.assertTrue(self._messages_to(newcomer),
                        "newly subscribed resident was NOT alerted")
