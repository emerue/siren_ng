"""
Coordinator policy and the transactional service layer behind every workflow action.

This module is the single place where an incident's lifecycle is advanced by a human.
The admin is presentation only — it calls in here.

Two BRD invariants govern everything below:

  §8  Human-verify-before-broadcast. `confirm_and_alert` is the ONLY function that
      calls `_post_verification_actions`, and it refuses unless the incident is
      still DETECTED. There is no time-based or automatic path.

  §8  Promise invariant. Outbound copy is chosen from fixed templates. No caller
      can pass free text through to a reporter or a subscriber.

Every function is compare-and-set inside one transaction, so a double-tap or a
re-POSTed form cannot fire a broadcast twice.
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

COORDINATOR_GROUP = "Coordinator"

# Fixed rejection reasons. Rendered as a <select>; a coordinator can never type
# free text that reaches a reporter.
REJECTION_REASONS = [
    ("NOT_EMERGENCY", "Not an emergency"),
    ("DUPLICATE", "Duplicate of a report already in the queue"),
    ("INSUFFICIENT_DETAIL", "Not enough detail to act on"),
    ("OUT_OF_AREA", "Outside the Lagos coverage area"),
    ("TEST_OR_PRANK", "Test message or prank"),
    ("UNINTELLIGIBLE", "Could not understand the report"),
]
REJECTION_LABELS = dict(REJECTION_REASONS)

# Marker prefixes. Used to dedupe without adding model fields, and readable in
# the same timeline the coordinator already looks at.
SLA_NOTE_PREFIX = "SLA breach: "
INFO_NOTE_PREFIX = "Requested more detail from reporter."

# A reporter is mid-emergency. Never text them twice in quick succession.
INFO_COOLDOWN = timedelta(minutes=10)

# WhatsApp only accepts free-form replies inside the 24h service window.
SERVICE_WINDOW = timedelta(hours=24)


# ── Identity ─────────────────────────────────────────────────────────────────

def is_coordinator(user) -> bool:
    """True for an active staff user in the Coordinator group who is NOT a superuser.

    Superusers deliberately fail this check so every policy branch falls through
    to Django's stock behaviour for them.
    """
    if not (user and getattr(user, "is_authenticated", False)
            and user.is_active and user.is_staff and not user.is_superuser):
        return False
    cached = getattr(user, "_siren_is_coordinator", None)
    if cached is None:
        cached = user.groups.filter(name=COORDINATOR_GROUP).exists()
        user._siren_is_coordinator = cached
    return cached


def actor_name(request) -> str:
    """Username of whoever performed the action, for the audit trail.

    Tolerates `request=None` because the existing bulk-action tests invoke the
    admin actions directly with no request.
    """
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return user.get_username()[:200]
    return "admin"


# ── Preconditions (shared by the service layer and the template buttons) ─────

def can_confirm(incident) -> bool:
    return incident.status == "DETECTED"


def can_reject(incident) -> bool:
    # DETECTED only. Rejecting a VERIFIED incident would send "could not be
    # verified" AFTER the LGA broadcast already went out — a promise-invariant
    # contradiction the reporter would rightly not understand.
    return incident.status == "DETECTED"


def can_resolve(incident) -> bool:
    return incident.status in ("VERIFIED", "AGENCY_NOTIFIED")


def within_service_window(incident) -> bool:
    return timezone.now() - incident.created_at < SERVICE_WINDOW


def can_request_info(incident) -> bool:
    return (
        incident.status == "DETECTED"
        and bool(incident.reporter_phone)
        and within_service_window(incident)
    )


# ── Workflow actions ─────────────────────────────────────────────────────────

@transaction.atomic
def confirm_and_alert(incident_id, actor: str) -> bool:
    """DETECTED → VERIFIED, then fan out. The only broadcast trigger in the system.

    Returns False (and broadcasts nothing) if the incident has already moved on,
    which is what makes a re-POST or a double-tap safe.
    """
    from apps.incidents.models import Incident
    from apps.incidents.tasks import _transition, _post_verification_actions

    incident = Incident.objects.select_for_update().get(pk=incident_id)
    # The status precondition is the primary guard: select_for_update is a real
    # lock on Postgres but a silent no-op on SQLite, where tests run.
    if not can_confirm(incident):
        return False

    _transition(incident, "VERIFIED", actor,
                "Confirmed by coordinator; neighbours alerted.")
    incident.save(update_fields=["status", "updated_at"])

    # Deferred to commit: _post_verification_actions queues Celery tasks, and a
    # worker can dequeue before this transaction lands, read DETECTED, and bail.
    transaction.on_commit(lambda: _post_verification_actions(incident))
    logger.info("coordinator confirm: incident %s by %s", incident_id, actor)
    return True


@transaction.atomic
def reject(incident_id, actor: str, reason_code: str) -> bool:
    """DETECTED → REJECTED with a reason from the fixed list."""
    from apps.incidents.models import Incident
    from apps.incidents.tasks import _transition, _notify_rejected

    label = REJECTION_LABELS.get(reason_code)
    if label is None:
        # Anything not in the fixed list is rejected outright rather than
        # coerced — an unknown code means a tampered form.
        raise ValueError(f"unknown rejection reason: {reason_code!r}")

    incident = Incident.objects.select_for_update().get(pk=incident_id)
    if not can_reject(incident):
        return False

    _transition(incident, "REJECTED", actor, label)
    incident.save(update_fields=["status", "updated_at"])
    transaction.on_commit(lambda: _notify_rejected(incident, label))
    logger.info("coordinator reject: incident %s by %s (%s)", incident_id, actor, reason_code)
    return True


@transaction.atomic
def resolve(incident_id, actor: str) -> bool:
    """VERIFIED / AGENCY_NOTIFIED → RESOLVED, closing the loop with the reporter."""
    from apps.incidents.models import Incident
    from apps.incidents.tasks import _transition
    from apps.whatsapp.tasks import notify_reporter_resolved

    incident = Incident.objects.select_for_update().get(pk=incident_id)
    if not can_resolve(incident):
        return False

    _transition(incident, "RESOLVED", actor, "Resolved by coordinator.")
    incident.resolved_at = timezone.now()
    incident.save(update_fields=["status", "resolved_at", "updated_at"])
    transaction.on_commit(lambda: notify_reporter_resolved.delay(str(incident.id)))
    logger.info("coordinator resolve: incident %s by %s", incident_id, actor)
    return True


@transaction.atomic
def request_more_info(incident_id, actor: str) -> bool:
    """Ask the reporter for more detail. Status is unchanged — it stays queued.

    Sends a FIXED template; no free text is accepted from the caller.
    """
    from apps.incidents.models import Incident, ResponseLog
    from apps.whatsapp import templates as tmpl
    from apps.whatsapp.i18n import get_language
    from apps.whatsapp.tasks import send_whatsapp_text

    incident = Incident.objects.select_for_update().get(pk=incident_id)
    if not can_request_info(incident):
        return False

    recent = (incident.response_logs
              .filter(note__startswith=INFO_NOTE_PREFIX)
              .order_by("-created_at")
              .first())
    if recent and timezone.now() - recent.created_at < INFO_COOLDOWN:
        return False

    # Written directly rather than via _transition: the status is not changing,
    # and _transition would push a WebSocket update for a non-event.
    ResponseLog.objects.create(
        incident=incident,
        from_status=incident.status,
        to_status=incident.status,
        actor=actor,
        note=INFO_NOTE_PREFIX,
    )

    phone = incident.reporter_phone
    body = tmpl.coordinator_more_info(get_language(phone))
    transaction.on_commit(lambda: send_whatsapp_text.delay(phone, body))
    logger.info("coordinator requested more info: incident %s by %s", incident_id, actor)
    return True
