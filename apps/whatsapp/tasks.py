import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def send_whatsapp_text(to_number, message):
    """Base Twilio send — all outbound messages go through here."""
    try:
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=f'whatsapp:{to_number}',
            body=message,
        )
    except Exception as exc:
        logger.error("send_whatsapp_text failed to %s: %s", to_number, exc)


@shared_task
def notify_reporter_verified(incident_id):
    from apps.incidents.models import Incident
    from apps.whatsapp import templates as tmpl

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        return

    if not incident.reporter_phone:
        return

    send_whatsapp_text.delay(
        incident.reporter_phone,
        tmpl.verified_notification(incident),
    )


@shared_task
def notify_reporter_rejected(incident_id, reason):
    from apps.incidents.models import Incident
    from apps.whatsapp import templates as tmpl

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        return

    if not incident.reporter_phone:
        return

    send_whatsapp_text.delay(
        incident.reporter_phone,
        tmpl.rejected_notification(reason),
    )


@shared_task
def notify_reporter_verifying(incident_id):
    from apps.incidents.models import Incident
    from apps.whatsapp import templates as tmpl

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        return

    if not incident.reporter_phone:
        return

    send_whatsapp_text.delay(
        incident.reporter_phone,
        tmpl.verifying_notification(incident),
    )


@shared_task
def post_community_announcement(incident_id):
    """Post verified incident to zone community group (stub — wire up when group number set)."""
    logger.info("post_community_announcement: incident %s — community group not yet configured.", incident_id)
