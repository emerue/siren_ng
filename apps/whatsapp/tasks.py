import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def handle_whatsapp_message(from_number, body, media_urls, location):
    """Wrapper so route_inbound runs in a Celery worker, not in the Twilio request cycle."""
    from apps.whatsapp.handlers import route_inbound
    route_inbound(from_number, body, media_urls or [], location)


@shared_task
def send_whatsapp_text(to_number, message):
    """Base Twilio send -- all outbound messages go through here."""
    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        to_whatsapp = (
            to_number if str(to_number).startswith('whatsapp:')
            else f'whatsapp:{to_number}'
        )
        msg = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            to=to_whatsapp,
            body=message,
        )
        logger.info(
            "send_whatsapp_text: sent to %s with status %s",
            to_whatsapp, getattr(msg, 'status', 'unknown')
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
        logger.error("notify_reporter_verified: Incident %s not found", incident_id)
        return

    if not incident.reporter_phone:
        logger.error(
            "notify_reporter_verified: No reporter_phone for incident %s. "
            "Cannot send verification result.",
            incident_id,
        )
        return

    if incident.status != 'VERIFIED':
        logger.info(
            "notify_reporter_verified: Incident %s status is %s, not VERIFIED. "
            "Skipping notification.",
            incident_id,
            incident.status,
        )
        return

    try:
        logger.info(
            "notify_reporter_verified: Sending verification result to %s for incident %s",
            incident.reporter_phone,
            incident_id,
        )
        send_whatsapp_text.delay(
            incident.reporter_phone,
            tmpl.verified_notification(incident),
        )
        logger.info(
            "notify_reporter_verified: Message queued for %s",
            incident.reporter_phone,
        )
    except Exception as exc:
        logger.error(
            "notify_reporter_verified: Failed to send message to %s: %s",
            incident.reporter_phone,
            exc,
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
def notify_reporter_resolved(incident_id):
    """
    Send closure notification to the original reporter when incident is resolved.
    Fires once when status transitions to RESOLVED.
    """
    from apps.incidents.models import Incident
    from django.utils import timezone

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        logger.error("notify_reporter_resolved: Incident %s not found", incident_id)
        return

    if not incident.reporter_phone:
        logger.info("notify_reporter_resolved: No phone for incident %s", incident_id)
        return

    # Calculate resolution time
    if incident.resolved_at and incident.created_at:
        delta = incident.resolved_at - incident.created_at
        total_minutes = int(delta.total_seconds() / 60)
        if total_minutes >= 60:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            resolution_time = (
                f"{hours} hour{'s' if hours > 1 else ''}, "
                f"{minutes} minute{'s' if minutes != 1 else ''}"
            )
        else:
            resolution_time = f"{total_minutes} minute{'s' if total_minutes != 1 else ''}"
    else:
        resolution_time = "time not recorded"

    # Count distinct responders from response logs
    responder_count = incident.response_logs.filter(
        to_status__in=['RESPONDING', 'AGENCY_NOTIFIED']
    ).values('actor').distinct().count()

    incident_type = incident.get_incident_type_display() if incident.incident_type else "Emergency"
    zone = incident.zone_name or "Lagos"
    tracking_url = f"https://sirenng-production.up.railway.app/track/{incident.id}"

    message = f"\u2705 Update: Your report has been resolved.\n\n"
    message += f"{incident_type} \u2014 {zone}\n"
    message += f"Resolved in {resolution_time}.\n"

    if responder_count > 0:
        message += f"{responder_count} responder{'s' if responder_count > 1 else ''} assisted.\n"

    if incident.total_donations_kobo > 0:
        naira = incident.total_donations_kobo / 100
        message += f"\u20a6{naira:,.0f} raised for relief.\n"

    message += f"\nThank you for reporting. You helped protect your community."
    message += f"\n\nTrack details: {tracking_url}"

    try:
        send_whatsapp_text.delay(incident.reporter_phone, message)
    except Exception as e:
        logger.error("notify_reporter_resolved: Failed to send to %s: %s", incident.reporter_phone, e)


@shared_task
def process_whatsapp_media(incident_id, media_urls):
    """
    Download Twilio temporary URLs and persist them to Supabase + IncidentMedia.
    Must run as soon as possible after incident creation — Twilio URLs expire.
    """
    from apps.incidents.models import Incident, IncidentMedia
    from services.media_service import upload_twilio_media_to_supabase

    if not media_urls:
        return

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        logger.error("process_whatsapp_media: incident %s not found", incident_id)
        return

    success = 0
    for url in media_urls[:5]:  # BRD cap: 5 files per incident
        if not url:
            continue
        result = upload_twilio_media_to_supabase(url, str(incident.id))
        if result:
            try:
                IncidentMedia.objects.create(
                    incident=incident,
                    media_type=result['media_type'],
                    public_url=result['public_url'],
                    storage_path=result['storage_path'],
                    file_size=result['file_size'],
                )
                success += 1
            except Exception as e:
                logger.error("process_whatsapp_media: IncidentMedia create failed: %s", e)

    logger.info(
        "process_whatsapp_media: %d/%d stored for incident %s",
        success, min(len(media_urls), 5), incident_id,
    )


@shared_task
def post_community_announcement(incident_id):
    """Post verified incident to zone community group (stub -- wire up when group number set)."""
    logger.info("post_community_announcement: incident %s -- community group not yet configured.", incident_id)
