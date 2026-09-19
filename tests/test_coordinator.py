"""
Coordinator console regression suite.

The console exists so a non-superuser can verify incidents. These tests pin the
two things that makes safe:

  - a coordinator's reach is genuinely bounded (no deletes, no other models, no
    reporter identity), enforced server-side rather than by hiding buttons
  - nothing broadcasts without a deliberate human POST, and never twice
"""
import datetime
import hashlib
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.admin.sites import AdminSite
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.incidents.admin import IncidentAdmin
from apps.incidents.coordinator import COORDINATOR_GROUP, is_coordinator
from apps.incidents.models import Incident, ResponseLog

User = get_user_model()

REPORTER_PHONE = "whatsapp:+2348116962682"


def make_incident(**kwargs):
    defaults = dict(
        source="WHATSAPP",
        reporter_hash=hashlib.sha256(b"reporter").hexdigest(),
        reporter_phone=REPORTER_PHONE,
        description="Fire at Isolo market, near the bus stop",
        incident_type="FIRE",
        severity="HIGH",
        status="DETECTED",
        zone_name="Oshodi-Isolo",
        ai_raw_response={"zone_name": "Oshodi-Isolo", "incident_type": "FIRE"},
        ai_confidence=0.94,
        fraud_score=0.05,
    )
    defaults.update(kwargs)
    return Incident.objects.create(**defaults)


class CoordinatorGroupCommandTests(TestCase):
    def test_creates_group_with_least_privilege(self):
        call_command("setup_coordinator_group", verbosity=0)
        group = Group.objects.get(name=COORDINATOR_GROUP)
        codenames = set(group.permissions.values_list("codename", flat=True))
        self.assertEqual(
            codenames,
            {"view_incident", "change_incident", "view_incidentmedia", "view_responselog"},
        )
        # The dangerous ones must be absent, not merely hidden in the UI.
        for forbidden in ("delete_incident", "add_incident", "delete_responselog"):
            self.assertNotIn(forbidden, codenames)

    def test_is_idempotent_and_self_healing(self):
        call_command("setup_coordinator_group", verbosity=0)
        group = Group.objects.get(name=COORDINATOR_GROUP)
        before = set(group.permissions.values_list("codename", flat=True))

        # Someone hand-adds delete rights in the admin UI.
        group.permissions.add(Permission.objects.get(codename="delete_incident"))
        call_command("setup_coordinator_group", verbosity=0)

        after = set(group.permissions.values_list("codename", flat=True))
        self.assertEqual(before, after, "re-running should revoke drift")

    def test_promotes_user_to_staff_coordinator(self):
        user = User.objects.create_user("ada", password="x")
        call_command("setup_coordinator_group", "--user", "ada", verbosity=0)
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(is_coordinator(user))


@override_settings(ALLOWED_HOSTS=["*"])
class CoordinatorAccessTests(TestCase):
    """What a coordinator can and cannot reach."""

    def setUp(self):
        call_command("setup_coordinator_group", verbosity=0)
        self.user = User.objects.create_user("ada", password="pw", is_staff=True)
        self.user.groups.add(Group.objects.get(name=COORDINATOR_GROUP))
        self.client.force_login(self.user)
        self.incident = make_incident()

    def test_cannot_reach_other_apps(self):
        for path in ("/admin/auth/user/", "/admin/auth/group/",
                     "/admin/subscriptions/lgasubscription/",
                     "/admin/responders/responder/"):
            response = self.client.get(path)
            self.assertIn(response.status_code, (302, 403, 404), f"reachable: {path}")

    def test_admin_index_lists_only_incidents(self):
        body = self.client.get("/admin/").content.decode().lower()
        for absent in ("subscriptions", "responders", "organisations", "users", "groups"):
            self.assertNotIn(f">{absent}<", body)

    def test_reporter_identity_never_rendered(self):
        url = reverse("admin:incidents_incident_change", args=[self.incident.pk])
        body = self.client.get(url).content.decode()
        self.assertNotIn("2348116962682", body)
        self.assertNotIn(self.incident.reporter_hash, body)
        self.assertIn("••••2682", body)  # masked form is shown instead

    def test_cannot_filter_by_reporter_phone(self):
        """The changelist must not work as a phone-number oracle."""
        response = self.client.get(
            "/admin/incidents/incident/?reporter_phone__startswith=%2B23481"
        )
        self.assertIn(response.status_code, (302, 400))

    def test_cannot_delete_or_add(self):
        admin = IncidentAdmin(Incident, AdminSite())
        request = RequestFactory().get("/admin/incidents/incident/")
        request.user = self.user
        self.assertFalse(admin.has_delete_permission(request, self.incident))
        self.assertFalse(admin.has_add_permission(request))
        self.assertEqual(admin.get_actions(request), {})

    def test_status_is_not_editable_through_the_form(self):
        """A crafted POST cannot move status — the field is never bound."""
        url = reverse("admin:incidents_incident_change", args=[self.incident.pk])
        self.client.post(url, {
            "incident_type": "FIRE", "severity": "HIGH",
            "zone_name": "Oshodi-Isolo", "coordinator_note": "",
            "status": "RESOLVED",
        })
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, "DETECTED")


@override_settings(ALLOWED_HOSTS=["*"])
class CoordinatorActionTests(TestCase):
    """The workflow actions: only a POST broadcasts, and only once."""

    def setUp(self):
        call_command("setup_coordinator_group", verbosity=0)
        self.user = User.objects.create_user("ada", password="pw", is_staff=True)
        self.user.groups.add(Group.objects.get(name=COORDINATOR_GROUP))
        self.client.force_login(self.user)
        self.incident = make_incident()

    def _url(self, name):
        return reverse(f"admin:incidents_incident_coordinator_{name}",
                       args=[self.incident.pk])

    def test_get_on_action_urls_never_broadcasts(self):
        with patch("apps.incidents.tasks._post_verification_actions") as broadcast:
            for name in ("confirm", "reject", "resolve", "request_info"):
                self.client.get(self._url(name))
            self.assertEqual(broadcast.call_count, 0)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, "DETECTED")

    def test_confirm_broadcasts_exactly_once(self):
        with patch("apps.incidents.tasks._post_verification_actions") as broadcast:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self._url("confirm"))
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self._url("confirm"))  # double-tap / re-POST
            self.assertEqual(broadcast.call_count, 1)

        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, "VERIFIED")

    def test_confirm_records_the_real_coordinator(self):
        with patch("apps.incidents.tasks._post_verification_actions"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self._url("confirm"))
        log = ResponseLog.objects.filter(incident=self.incident,
                                         to_status="VERIFIED").first()
        self.assertEqual(log.actor, "ada", "the acting coordinator must be auditable")

    def test_reject_requires_a_known_reason(self):
        with patch("apps.incidents.tasks._notify_rejected") as notify:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self._url("reject"), {"reason": "<script>alert(1)</script>"})
            notify.assert_not_called()
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, "DETECTED")

    def test_reject_with_valid_reason_records_the_label(self):
        with patch("apps.incidents.tasks._notify_rejected"):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self._url("reject"), {"reason": "NOT_EMERGENCY"})
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, "REJECTED")
        log = ResponseLog.objects.filter(incident=self.incident,
                                         to_status="REJECTED").first()
        self.assertEqual(log.note, "Not an emergency")

    def test_cannot_reject_after_broadcast(self):
        """Rejecting a VERIFIED incident would contradict an alert already sent."""
        from apps.incidents import coordinator as coord
        self.incident.status = "VERIFIED"
        self.incident.save(update_fields=["status"])
        with patch("apps.incidents.tasks._notify_rejected") as notify:
            self.assertFalse(coord.reject(self.incident.pk, "ada", "NOT_EMERGENCY"))
            notify.assert_not_called()

    def test_request_more_info_keeps_it_queued_and_does_not_repeat(self):
        from apps.whatsapp.tasks import send_whatsapp_text
        with patch.object(send_whatsapp_text, "delay") as send:
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self._url("request_info"))
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(self._url("request_info"))  # cooldown blocks this
            self.assertEqual(send.call_count, 1, "must not double-text a reporter")

        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, "DETECTED", "stays in the queue")

    def test_non_coordinator_staff_cannot_act(self):
        other = User.objects.create_user("intern", password="pw", is_staff=True)
        self.client.force_login(other)
        with patch("apps.incidents.tasks._post_verification_actions") as broadcast:
            response = self.client.post(self._url("confirm"))
            self.assertIn(response.status_code, (302, 403))
            self.assertEqual(broadcast.call_count, 0)


@override_settings(ALLOWED_HOSTS=["*"])
class SuperuserUnchangedTests(TestCase):
    """The superuser admin must behave exactly as it did before this work."""

    def setUp(self):
        self.su = User.objects.create_superuser("root", "root@example.com", "pw")
        self.admin = IncidentAdmin(Incident, AdminSite())
        self.request = RequestFactory().get("/admin/incidents/incident/")
        self.request.user = self.su

    def test_superuser_is_not_treated_as_coordinator(self):
        self.assertFalse(is_coordinator(self.su))

    def test_list_display_and_fieldsets_are_the_class_defaults(self):
        self.assertEqual(list(self.admin.get_list_display(self.request)),
                         IncidentAdmin.list_display)
        self.assertEqual(list(self.admin.get_list_filter(self.request)),
                         IncidentAdmin.list_filter)
        self.assertEqual(list(self.admin.get_readonly_fields(self.request)),
                         IncidentAdmin.readonly_fields)

    def test_superuser_keeps_bulk_actions_and_delete(self):
        self.assertIn("mark_verified", self.admin.get_actions(self.request))
        self.assertTrue(self.admin.has_delete_permission(self.request))
        self.assertTrue(self.admin.has_add_permission(self.request))


class CoverageWindowTests(TestCase):
    """Out-of-hours acknowledgment must be honest about coordinator availability."""

    def _at(self, hour, minute=0):
        return timezone.make_aware(
            datetime.datetime(2026, 8, 20, hour, minute),
            timezone.get_current_timezone(),
        )

    @override_settings(COORDINATOR_COVERAGE_START="07:00",
                       COORDINATOR_COVERAGE_END="21:00")
    def test_boundaries(self):
        from utils.coverage import is_within_coverage
        self.assertFalse(is_within_coverage(self._at(6, 59)))
        self.assertTrue(is_within_coverage(self._at(7, 0)))
        self.assertTrue(is_within_coverage(self._at(20, 59)))
        self.assertFalse(is_within_coverage(self._at(21, 0)))

    @override_settings(COORDINATOR_COVERAGE_START="21:00",
                       COORDINATOR_COVERAGE_END="07:00")
    def test_wraps_over_midnight(self):
        from utils.coverage import is_within_coverage
        self.assertTrue(is_within_coverage(self._at(23, 0)))
        self.assertTrue(is_within_coverage(self._at(3, 0)))
        self.assertFalse(is_within_coverage(self._at(12, 0)))

    @override_settings(COORDINATOR_COVERAGE_START="not-a-time")
    def test_malformed_setting_never_raises(self):
        """This runs inside the Twilio webhook path; it must not break intake."""
        from utils.coverage import is_within_coverage
        self.assertIsInstance(is_within_coverage(self._at(12, 0)), bool)

    def test_out_of_hours_copy_is_honest_and_clean(self):
        from apps.whatsapp import templates as tmpl
        banned = ["on the way", "on their way", "dispatched", "help is coming"]
        for lang in ("en", "pcm"):
            for message in (tmpl.received_ack_out_of_hours(lang),
                            tmpl.coordinator_more_info(lang)):
                low = message.lower()
                for phrase in banned:
                    self.assertNotIn(phrase, low)
            # Must not imply someone is reading it right now.
            self.assertIn("767", tmpl.received_ack_out_of_hours(lang))


@override_settings(ALLOWED_HOSTS=["*"],
                   COORDINATOR_COVERAGE_START="00:00",
                   COORDINATOR_COVERAGE_END="23:59",
                   COORDINATOR_ESCALATION_MINUTES=30)
class SlaEscalationTests(TestCase):
    def test_flags_stale_reports_once_and_never_verifies(self):
        from apps.incidents.tasks import check_coordinator_sla
        from apps.incidents.coordinator import SLA_NOTE_PREFIX

        incident = make_incident()
        Incident.objects.filter(pk=incident.pk).update(
            created_at=timezone.now() - datetime.timedelta(minutes=45)
        )

        with patch("apps.incidents.tasks._post_verification_actions") as broadcast:
            check_coordinator_sla()
            check_coordinator_sla()  # must not re-flag
            broadcast.assert_not_called()

        flags = ResponseLog.objects.filter(incident=incident, actor="system",
                                           note__startswith=SLA_NOTE_PREFIX)
        self.assertEqual(flags.count(), 1)
        incident.refresh_from_db()
        self.assertEqual(incident.status, "DETECTED", "escalation must never verify")

    def test_ignores_fresh_reports(self):
        from apps.incidents.tasks import check_coordinator_sla
        make_incident()
        check_coordinator_sla()
        self.assertEqual(ResponseLog.objects.filter(actor="system").count(), 0)
