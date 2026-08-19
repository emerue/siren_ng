"""
Security regression suite for the Siren.ng BRD invariants.

Each test corresponds to a rule that must never silently regress. If a future
change reintroduces one of these vulnerabilities, the suite fails.

Invariants covered (BRD §7 security, §8 promise invariant, §5.1.2 human-front
verification):
  - reporter phone never leaves the system through any read surface
  - only a human coordinator can cause a broadcast
  - AI output is untrusted data, never authority
  - privileged state transitions require staff
  - user-supplied URLs cannot reach the public incident page
  - rate limiting is keyed on normalised phone hash, never IP
  - Twilio signatures are validated before any processing
"""
import hashlib
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

# The API authenticates with JWT only (no SessionAuthentication), so
# django's client.login() does NOT authenticate API requests. Tests use
# DRF's APIClient + force_authenticate to exercise the real permission
# logic independently of the token transport.

from apps.incidents.models import Incident

User = get_user_model()

LOCMEM_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
}

REPORTER_PHONE = "whatsapp:+2348012345678"


def make_incident(**kwargs):
    defaults = dict(
        source="WHATSAPP",
        reporter_hash=hashlib.sha256(b"reporter").hexdigest(),
        reporter_phone=REPORTER_PHONE,
        description="Fire at Isolo market",
        incident_type="FIRE",
        severity="HIGH",
        status="VERIFIED",
        zone_name="Oshodi-Isolo",
        ai_raw_response={"reasoning": "internal triage note"},
        ai_confidence=0.9,
        fraud_score=0.05,
    )
    defaults.update(kwargs)
    return Incident.objects.create(**defaults)


@override_settings(ALLOWED_HOSTS=["*"])
class ReporterPhonePrivacyTests(TestCase):
    """BRD §7: reporter_phone must never appear in API responses."""

    def setUp(self):
        self.incident = make_incident()

    def _assert_no_phone(self, payload):
        blob = json.dumps(payload)
        self.assertNotIn("2348012345678", blob, "raw reporter phone leaked")
        self.assertNotIn("reporter_phone", blob)
        self.assertNotIn("reporter_hash", blob)

    def test_phone_not_in_incident_list(self):
        self._assert_no_phone(self.client.get("/api/incidents/").json())

    def test_phone_not_in_active_incidents(self):
        self._assert_no_phone(self.client.get("/api/incidents/active/").json())

    def test_phone_not_in_incident_detail(self):
        r = self.client.get(f"/api/incidents/{self.incident.id}/")
        self._assert_no_phone(r.json())

    def test_phone_not_in_public_tracking_page(self):
        r = self.client.get(f"/api/incidents/{self.incident.id}/track/")
        self._assert_no_phone(r.json())

    def test_ai_internals_not_public(self):
        """Internal triage signals are coordinator-only."""
        body = self.client.get(f"/api/incidents/{self.incident.id}/").json()
        for field in ("ai_raw_response", "fraud_score", "ai_confidence"):
            self.assertNotIn(field, body)

    def test_staff_sees_triage_fields_but_still_no_phone(self):
        staff = User.objects.create_user("coord", password="x", is_staff=True)
        api = APIClient()
        api.force_authenticate(user=staff)
        body = api.get(f"/api/incidents/{self.incident.id}/").json()
        self.assertIn("ai_confidence", body)
        self._assert_no_phone(body)

    def test_phone_not_in_websocket_payload(self):
        from apps.incidents.consumers import broadcast_update
        captured = {}
        with patch("apps.incidents.consumers.get_channel_layer") as layer:
            layer.return_value.group_send = lambda group, payload: captured.update(payload)
            with patch("apps.incidents.consumers.async_to_sync", lambda f: f):
                broadcast_update(self.incident)
        blob = json.dumps(captured, default=str)
        self.assertNotIn("2348012345678", blob)
        self.assertNotIn("reporter_phone", blob)


@override_settings(ALLOWED_HOSTS=["*"])
class HumanVerificationGateTests(TestCase):
    """BRD §8 companion rule: only human-verified incidents are ever broadcast."""

    def test_ai_cannot_verify_or_broadcast(self):
        """AI classification must leave the incident in DETECTED and fire nothing."""
        from apps.incidents.tasks import verify_incident_ai

        incident = make_incident(status="DETECTED", incident_type="", zone_name="")
        ai_payload = {
            "eligible": True, "incident_type": "FIRE", "severity": "HIGH",
            "ai_confidence": 0.99, "fraud_score": 0.0,
            "is_infrastructure": False, "zone_name": "Oshodi-Isolo",
        }
        with patch("apps.incidents.tasks._call_ai", return_value=ai_payload), \
             patch("apps.incidents.tasks._post_verification_actions") as broadcast:
            verify_incident_ai(str(incident.id))

        incident.refresh_from_db()
        self.assertEqual(incident.status, "DETECTED")
        broadcast.assert_not_called()

    def test_ai_output_cannot_grant_privileged_state(self):
        """A hostile model reply claiming verification is ignored."""
        from apps.incidents.tasks import _validate_ai_result
        result = _validate_ai_result({
            "eligible": True, "verified": True, "status": "VERIFIED",
            "incident_type": "FIRE", "severity": "CRITICAL",
            "ai_confidence": 1.0, "fraud_score": 0.0,
        })
        self.assertNotIn("verified", result)
        self.assertNotIn("status", result)

    def test_ai_output_enums_are_enforced(self):
        from apps.incidents.tasks import _validate_ai_result
        result = _validate_ai_result({
            "eligible": True,
            "incident_type": "<script>alert(1)</script>",
            "severity": "GODMODE",
            "ai_confidence": 99, "fraud_score": -5,
            "zone_name": "X" * 400,
        })
        self.assertEqual(result["incident_type"], "")
        self.assertEqual(result["severity"], "MEDIUM")
        self.assertEqual(result["ai_confidence"], 1.0)
        self.assertEqual(result["fraud_score"], 0.0)
        self.assertLessEqual(len(result["zone_name"]), 120)

    def test_coordinator_confirm_triggers_actions_once(self):
        """The admin action is the single broadcast trigger."""
        from apps.incidents.admin import IncidentAdmin
        from django.contrib.admin.sites import AdminSite

        incident = make_incident(status="DETECTED")
        admin = IncidentAdmin(Incident, AdminSite())
        with patch("apps.incidents.tasks._post_verification_actions") as broadcast:
            admin.mark_verified(None, Incident.objects.filter(pk=incident.pk))
        incident.refresh_from_db()
        self.assertEqual(incident.status, "VERIFIED")
        self.assertEqual(broadcast.call_count, 1)


@override_settings(ALLOWED_HOSTS=["*"])
class PrivilegedEndpointAuthorizationTests(TestCase):
    """Public and ordinary authenticated users cannot move incident state."""

    def setUp(self):
        self.incident = make_incident()
        self.dispatch_url = f"/api/incidents/{self.incident.id}/dispatch/"
        self.resolve_url = f"/api/incidents/{self.incident.id}/resolve/"

    def test_anonymous_cannot_dispatch_or_resolve(self):
        for url in (self.dispatch_url, self.resolve_url):
            self.assertIn(self.client.patch(url).status_code, (401, 403))

    def test_non_staff_user_cannot_dispatch_or_resolve(self):
        user = User.objects.create_user("bystander", password="x")
        api = APIClient()
        api.force_authenticate(user=user)
        for url in (self.dispatch_url, self.resolve_url):
            self.assertEqual(api.patch(url).status_code, 403)

    def test_staff_can_dispatch(self):
        staff = User.objects.create_user("coord", password="x", is_staff=True)
        api = APIClient()
        api.force_authenticate(user=staff)
        self.assertEqual(api.patch(self.dispatch_url).status_code, 200)


@override_settings(ALLOWED_HOSTS=["*"])
class MediaUrlInjectionTests(TestCase):
    """User-supplied URLs must not reach the public incident page."""

    def setUp(self):
        self.incident = make_incident()
        self.url = f"/api/incidents/{self.incident.id}/media-urls/"

    def test_anonymous_cannot_attach_url(self):
        r = self.client.post(self.url, {"url": "https://evil.example/x.png"})
        self.assertEqual(r.status_code, 403)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.media_urls, [])

    def test_anonymous_cannot_remove_url(self):
        self.incident.media_urls = ["https://good.example/a.png"]
        self.incident.save(update_fields=["media_urls"])
        r = self.client.delete(
            self.url, data=json.dumps({"url": "https://good.example/a.png"}),
            content_type="application/json")
        self.assertEqual(r.status_code, 403)

    def _staff_client(self):
        staff = User.objects.create_user("coord", password="x", is_staff=True)
        api = APIClient()
        api.force_authenticate(user=staff)
        return api

    def test_staff_cannot_attach_javascript_url(self):
        api = self._staff_client()
        for payload in ("javascript:alert(1)", "data:text/html;base64,PHN2Zz4=",
                        "file:///etc/passwd", "not-a-url"):
            r = api.post(self.url, {"url": payload})
            self.assertEqual(r.status_code, 400, f"accepted unsafe URL: {payload}")

    def test_staff_can_attach_https_url(self):
        api = self._staff_client()
        r = api.post(self.url, {"url": "https://example.org/photo.jpg"})
        self.assertEqual(r.status_code, 200)


@override_settings(ALLOWED_HOSTS=["*"], CACHES=LOCMEM_CACHE)
class RateLimitTests(TestCase):
    """BRD §7: throttling keyed on normalised phone hash, never IP."""

    def setUp(self):
        cache.clear()

    def test_phone_variants_share_one_identity(self):
        from utils.ratelimit import phone_hash
        variants = [
            "whatsapp:+2348012345678", "+234 801 234 5678",
            "2348012345678", "08012345678", " whatsapp:+234-801-234-5678 ",
        ]
        self.assertEqual(len({phone_hash(v) for v in variants}), 1)

    def test_reformatting_does_not_reset_quota(self):
        """The old limiter hashed the raw string, so this bypassed the limit."""
        from utils.ratelimit import hit_rate_limit
        for _ in range(10):
            hit_rate_limit("whatsapp:+2348012345678", rate=10, window=60)
        self.assertTrue(hit_rate_limit("08012345678", rate=10, window=60))

    def test_limit_blocks_after_threshold(self):
        from utils.ratelimit import hit_rate_limit
        blocked = [hit_rate_limit("+2348011111111", rate=5, window=60) for _ in range(8)]
        self.assertFalse(any(blocked[:5]))
        self.assertTrue(blocked[-1])

    def test_masked_identity_contains_no_digits_of_number(self):
        from utils.ratelimit import masked
        self.assertNotIn("8012345678", masked(REPORTER_PHONE))


@override_settings(ALLOWED_HOSTS=["*"], CACHES=LOCMEM_CACHE)
class WebhookSignatureTests(TestCase):
    """Twilio signature validation must precede all processing."""

    def setUp(self):
        cache.clear()

    def test_missing_signature_rejected(self):
        r = self.client.post("/api/ingest/whatsapp/",
                             {"From": REPORTER_PHONE, "Body": "fire"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Incident.objects.count(), 0)

    def test_forged_signature_rejected(self):
        r = self.client.post("/api/ingest/whatsapp/",
                             {"From": REPORTER_PHONE, "Body": "fire"},
                             HTTP_X_TWILIO_SIGNATURE="not-a-real-signature")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Incident.objects.count(), 0)


@override_settings(ALLOWED_HOSTS=["*"], CACHES=LOCMEM_CACHE)
class WebIngestHardeningTests(TestCase):
    """The open web intake must not accept privileged or unbounded input."""

    def setUp(self):
        cache.clear()

    def test_client_supplied_media_urls_are_ignored(self):
        r = self.client.post("/api/ingest/web/", {
            "description": "Fire at the market",
            "media_urls": ["javascript:alert(1)"],
        }, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        incident = Incident.objects.get(id=r.json()["id"])
        self.assertEqual(incident.media_urls, [])

    def test_client_cannot_preset_incident_type(self):
        r = self.client.post("/api/ingest/web/", {
            "description": "Something happened", "incident_type": "EXPLOSION",
        }, content_type="application/json")
        self.assertEqual(Incident.objects.get(id=r.json()["id"]).incident_type, "")

    def test_description_is_bounded(self):
        r = self.client.post("/api/ingest/web/",
                             {"description": "A" * 10000},
                             content_type="application/json")
        self.assertLessEqual(len(Incident.objects.get(id=r.json()["id"]).description), 2000)

    def test_repeated_reports_are_throttled(self):
        codes = [
            self.client.post("/api/ingest/web/", {"description": f"report {i}"},
                             content_type="application/json").status_code
            for i in range(8)
        ]
        self.assertIn(429, codes)


class AuthorityForwardSSRFTests(TestCase):
    """The authority webhook must not be usable as an internal-network pivot."""

    def test_non_public_destinations_rejected(self):
        from apps.incidents.tasks import _is_safe_authority_url
        for url in ("http://example.org/hook", "https://127.0.0.1/hook",
                    "https://localhost/hook", "https://169.254.169.254/latest/meta-data/",
                    "https://10.0.0.5/hook", "ftp://example.org"):
            self.assertFalse(_is_safe_authority_url(url), f"allowed unsafe: {url}")


class PromiseInvariantTests(TestCase):
    """BRD §8: never claim a third party is responding."""

    BANNED = [
        "help is on the way", "on their way", "ambulance has been dispatched",
        "responders are on their way", "police are coming", "rescue team is coming",
    ]

    def test_core_loop_copy_is_clean(self):
        from types import SimpleNamespace
        import uuid
        from apps.whatsapp import templates as tmpl

        incident = SimpleNamespace(
            id=uuid.uuid4(), incident_type="FIRE", severity="HIGH",
            zone_name="Oshodi-Isolo", address_text="Isolo market",
        )
        messages = []
        for lang in ("en", "pcm"):
            messages += [
                tmpl.received_ack(lang),
                tmpl.verified_notification(incident, lang),
                tmpl.rejected_notification("test", lang),
                tmpl.resolution_closure(incident, lang),
            ]
        for message in messages:
            for phrase in self.BANNED:
                self.assertNotIn(phrase, message.lower(), f"promise invariant broken: {phrase}")

    def test_verified_message_credits_a_human(self):
        from types import SimpleNamespace
        import uuid
        from apps.whatsapp import templates as tmpl
        incident = SimpleNamespace(
            id=uuid.uuid4(), incident_type="FIRE", severity="HIGH",
            zone_name="Oshodi-Isolo", address_text="Isolo market",
        )
        message = tmpl.verified_notification(incident, "en")
        self.assertIn("coordinator", message.lower())
        self.assertNotIn("ai verified", message.lower())


@override_settings(ALLOWED_HOSTS=["*"])
class FeatureFlagExposureTests(TestCase):
    """The flag endpoint must expose booleans only — never configuration."""

    def test_features_endpoint_returns_only_booleans(self):
        body = self.client.get("/api/features/").json()["features"]
        self.assertTrue(all(isinstance(v, bool) for v in body.values()))

    def test_features_endpoint_leaks_no_secrets(self):
        blob = json.dumps(self.client.get("/api/features/").json()).lower()
        for marker in ("key", "secret", "token", "password", "url", "sid"):
            self.assertNotIn(marker, blob)

    def test_out_of_mvp_features_default_off(self):
        body = self.client.get("/api/features/").json()["features"]
        for flag in ("donations", "commute_shield", "vouching", "historical_layer"):
            self.assertFalse(body[flag], f"{flag} must default off")
