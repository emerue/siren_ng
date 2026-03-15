import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_location_subscribers(incident_id):
    """Alert all active POINT subscribers within their chosen radius of a verified incident."""
    from apps.incidents.models import Incident
    from apps.subscriptions.models import LocationSubscription, SubscriptionAlert
    from apps.whatsapp.tasks import send_whatsapp_text
    from apps.whatsapp import templates as tmpl
    from utils.distance import haversine_query
    from django.db import IntegrityError

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        return

    if not incident.location_lat or not incident.location_lng:
        logger.info("notify_location_subscribers: incident %s has no GPS — skipping", incident_id)
        return

    # Broad sweep — 10km. Per-subscriber radius filtered below.
    rows = haversine_query(
        table='subscriptions_locationsubscription',
        lat_field='location_lat',
        lng_field='location_lng',
        incident_lat=incident.location_lat,
        incident_lng=incident.location_lng,
        radius_km=10.0,
        extra_filters="AND is_active = TRUE AND subscription_type = 'POINT'",
        limit=500,
    )

    sent = 0
    for row in rows:
        try:
            sub = LocationSubscription.objects.get(id=row['id'])
        except LocationSubscription.DoesNotExist:
            continue

        # Individual radius filter
        if row['distance_km'] > sub.alert_radius_km:
            continue

        # Incident type filter
        if sub.incident_types and incident.incident_type not in sub.incident_types:
            continue

        # Dedup
        try:
            SubscriptionAlert.objects.create(
                subscription=sub,
                incident=incident,
                distance_km=row['distance_km'],
                alert_type='POINT',
            )
        except IntegrityError:
            continue  # Already alerted

        message = tmpl.subscription_alert(sub, incident, row['distance_km'])
        send_whatsapp_text.delay(sub.whatsapp_number, message)
        sent += 1

    logger.info("notify_location_subscribers: sent %d alerts for incident %s", sent, incident_id)


@shared_task
def notify_commute_shield(incident_id):
    """
    Find all active COMMUTE subscriptions whose home-office corridor passes
    within commute_buffer_km of this incident.
    Only runs during peak hours Lagos time (6-10am, 4-8pm).
    Always runs for CRITICAL severity.
    """
    import pytz
    from apps.incidents.models import Incident
    from apps.subscriptions.models import LocationSubscription, SubscriptionAlert
    from apps.whatsapp.tasks import send_whatsapp_text
    from utils.distance import point_to_line_distance
    from django.utils import timezone
    from django.db import IntegrityError

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        return

    if not incident.location_lat or not incident.location_lng:
        return

    # Peak-hour check (Lagos time)
    lagos_tz = pytz.timezone('Africa/Lagos')
    now_lagos = timezone.now().astimezone(lagos_tz)
    hour = now_lagos.hour
    is_peak = (6 <= hour < 10) or (16 <= hour < 20)
    # Still run for CRITICAL severity outside peak hours
    if not is_peak and incident.severity != 'CRITICAL':
        return

    commute_subs = LocationSubscription.objects.filter(
        subscription_type='COMMUTE',
        is_active=True,
        office_lat__isnull=False,
        office_lng__isnull=False,
    )

    sent = 0
    for sub in commute_subs:
        dist = point_to_line_distance(
            incident.location_lat, incident.location_lng,
            sub.location_lat, sub.location_lng,   # home
            sub.office_lat, sub.office_lng,        # office
        )

        if dist > sub.commute_buffer_km:
            continue

        try:
            SubscriptionAlert.objects.create(
                subscription=sub,
                incident=incident,
                distance_km=dist,
                alert_type='COMMUTE',
            )
        except IntegrityError:
            continue  # Already alerted

        message = _build_commute_alert(incident, sub, dist)
        send_whatsapp_text.delay(sub.whatsapp_number, message)
        sent += 1

    logger.info("notify_commute_shield: sent %d alerts for incident %s", sent, incident_id)


def _build_commute_alert(incident, sub, distance_km):
    type_labels = {
        'RTA': 'Road Accident', 'HAZARD': 'Downed wire / road hazard',
        'FLOOD': 'Flooding', 'FIRE': 'Fire', 'EXPLOSION': 'Explosion',
        'COLLAPSE': 'Building Collapse', 'DROWNING': 'Drowning',
    }
    return (
        f"COMMUTE SHIELD — {type_labels.get(incident.incident_type, incident.incident_type)}"
        f" on your route\n\n"
        f"{incident.address_text or incident.zone_name}\n"
        f"Severity: {incident.severity}\n"
        f"Distance from your corridor: {distance_km:.1f}km\n\n"
        f"Reply NEED RIDE to connect with people offering transport.\n\n"
        f"Full update: siren.ng/track/{incident.id}"
    )


@shared_task
def daily_safety_score_update():
    """
    For every active subscription, count verified incidents in the past 30 days
    within the alert radius (POINT) or corridor (COMMUTE).
    Score formula: starts at 100, -5 per incident, floor at 0.
    Save score and log entry.
    """
    from apps.subscriptions.models import LocationSubscription, SafetyScoreLog
    from utils.distance import haversine_query
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=30)

    for sub in LocationSubscription.objects.filter(is_active=True):
        rows = haversine_query(
            table='incidents_incident',
            lat_field='location_lat',
            lng_field='location_lng',
            incident_lat=sub.location_lat,
            incident_lng=sub.location_lng,
            radius_km=sub.alert_radius_km,
            extra_filters="AND status IN ('VERIFIED','RESPONDING','AGENCY_NOTIFIED','RESOLVED')",
            limit=100,
        )
        # Filter by date in Python
        recent = [r for r in rows if r.get('created_at') and r['created_at'] >= cutoff]

        score = max(0, 100 - (len(recent) * 5))
        reason = f"{len(recent)} verified incident(s) within {sub.alert_radius_km}km in last 30 days."

        sub.safety_score = score
        sub.save(update_fields=['safety_score'])

        SafetyScoreLog.objects.create(subscription=sub, score=score, reason=reason)

    logger.info("daily_safety_score_update: completed")


@shared_task
def send_commute_briefing():
    """
    Send daily route briefing to all active COMMUTE subscribers.
    Runs at 6:30am and 4:30pm. Checks for incidents on corridor in last 24 hours.
    """
    import pytz
    from apps.subscriptions.models import LocationSubscription
    from apps.incidents.models import Incident
    from apps.whatsapp.tasks import send_whatsapp_text
    from utils.distance import point_to_line_distance
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(hours=24)
    lagos_tz = pytz.timezone('Africa/Lagos')
    hour = timezone.now().astimezone(lagos_tz).hour
    is_morning = hour < 12

    for sub in LocationSubscription.objects.filter(
        subscription_type='COMMUTE', is_active=True,
        office_lat__isnull=False, office_lng__isnull=False,
    ):
        recent_incidents = Incident.objects.filter(
            status__in=['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED'],
            created_at__gte=cutoff,
            incident_type__in=['HAZARD', 'RTA', 'FLOOD'],
        ).exclude(location_lat=None)

        corridor_incidents = []
        for inc in recent_incidents:
            dist = point_to_line_distance(
                inc.location_lat, inc.location_lng,
                sub.location_lat, sub.location_lng,
                sub.office_lat, sub.office_lng,
            )
            if dist <= sub.commute_buffer_km:
                corridor_incidents.append((inc, dist))

        message = _build_briefing_message(sub, corridor_incidents, is_morning)
        send_whatsapp_text.delay(sub.whatsapp_number, message)

    logger.info("send_commute_briefing: completed (morning=%s)", is_morning)


def _build_briefing_message(sub, incidents, is_morning):
    greeting = "Good morning" if is_morning else "Evening check"
    direction = f"{sub.label} route"

    if not incidents:
        return (
            f"{greeting}. Your {direction}:\n\n"
            f"Clear — no incidents on your corridor in the last 24 hours.\n"
            f"Safety Score: {sub.safety_score}\n\n"
            f"Stay safe out there."
        )

    inc, dist = incidents[0]
    return (
        f"{greeting}. Your {direction}:\n\n"
        f"{inc.incident_type} reported {dist:.1f}km from your corridor.\n"
        f"{inc.address_text or inc.zone_name}\n"
        f"Status: {inc.status}\n\n"
        f"Safety Score: {sub.safety_score}\n\n"
        f"Full map: siren.ng/map"
    )
