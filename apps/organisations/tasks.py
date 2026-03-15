import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_nearest_organisations(incident_id):
    """Find and notify nearest verified organisations via WhatsApp."""
    from apps.incidents.models import Incident
    from apps.organisations.models import Organisation
    from apps.whatsapp.tasks import send_whatsapp_text
    from apps.whatsapp import templates as tmpl
    from utils.distance import haversine_query

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        return

    if not incident.location_lat or not incident.location_lng:
        logger.info("notify_nearest_organisations: incident %s has no GPS — skipping", incident_id)
        return

    rows = haversine_query(
        table='organisations_organisation',
        lat_field='location_lat',
        lng_field='location_lng',
        incident_lat=incident.location_lat,
        incident_lng=incident.location_lng,
        radius_km=10.0,
        extra_filters="AND status = 'VERIFIED'",
        limit=5,
    )

    notified = 0
    for row in rows:
        try:
            org = Organisation.objects.get(id=row['id'])
        except Organisation.DoesNotExist:
            continue

        if not org.contact_whatsapp:
            continue

        send_whatsapp_text.delay(
            org.contact_whatsapp,
            tmpl.org_notification(org, incident, row['distance_km']),
        )
        notified += 1

    logger.info("notify_nearest_organisations: notified %d orgs for incident %s", notified, incident_id)
