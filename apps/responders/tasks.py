import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_nearest_responders(incident_id, exclude_ids=None):
    """Find and notify nearest verified, available responders via WhatsApp."""
    from apps.incidents.models import Incident
    from apps.responders.models import Responder, ResponderDispatch
    from apps.whatsapp.tasks import send_whatsapp_text
    from apps.whatsapp import templates as tmpl
    from utils.distance import haversine_query
    from django.db import IntegrityError

    exclude_ids = exclude_ids or []

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        return

    if not incident.location_lat or not incident.location_lng:
        logger.info("notify_nearest_responders: incident %s has no GPS — skipping", incident_id)
        return

    rows = haversine_query(
        table='responders_responder',
        lat_field='home_lat',
        lng_field='home_lng',
        incident_lat=incident.location_lat,
        incident_lng=incident.location_lng,
        radius_km=10.0,
        extra_filters="AND status = 'VERIFIED' AND is_available = TRUE",
        limit=5,
    )

    notified = 0
    for row in rows:
        if str(row['id']) in [str(x) for x in exclude_ids]:
            continue
        try:
            responder = Responder.objects.get(id=row['id'])
        except Responder.DoesNotExist:
            continue

        try:
            ResponderDispatch.objects.create(responder=responder, incident=incident)
        except IntegrityError:
            continue  # Already dispatched

        send_whatsapp_text.delay(
            responder.whatsapp_number,
            tmpl.responder_notification(responder, incident, row['distance_km']),
        )
        notified += 1

    logger.info("notify_nearest_responders: notified %d responders for incident %s", notified, incident_id)
