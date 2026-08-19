import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def notify_location_subscribers(incident_id):
    """
    Alert all active LGA subscribers for a verified incident.
    Matches incident.zone_name against LGASubscription.lga using normalize_lga_name.
    """
    from apps.incidents.models import Incident
    from apps.subscriptions.models import LGASubscription, LGASubscriptionAlert
    from apps.whatsapp.tasks import send_whatsapp_text, send_whatsapp_template
    from django.db import IntegrityError, transaction

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        logger.error("notify_location_subscribers: incident %s not found", incident_id)
        return

    if not incident.zone_name:
        logger.info(
            "notify_location_subscribers: no zone_name for incident %s — skipping", incident_id
        )
        return

    lga = normalize_lga_name(incident.zone_name)
    if not lga:
        logger.warning(
            "notify_location_subscribers: could not normalize zone '%s' for incident %s",
            incident.zone_name, incident_id,
        )
        return

    subscribers = LGASubscription.objects.filter(
        lga=lga, is_active=True
    ).select_related('user')

    if not subscribers.exists():
        logger.info(
            "notify_location_subscribers: no subscribers for LGA '%s' (incident %s)",
            lga, incident_id,
        )
        return

    from django.conf import settings
    from apps.whatsapp.i18n import get_language

    incident_type_label = incident.incident_type or "Emergency"
    severity = incident.severity or "UNKNOWN"
    desc = incident.description[:150]
    tracking_url = f"{settings.SITE_URL}/track/{incident.id}"

    # v8 Promise Invariant (§8): state only what Siren did. Verification is
    # human-confirmed ("Siren coordinator"), never "AI verified" (§5.1.2).
    def _alert_message(lang):
        if lang == 'pcm':
            return (
                f"\U0001f6a8 SIREN ALERT — {lga}\n\n"
                f"{incident_type_label} for {incident.zone_name}\n"
                f"Severity: {severity}\n\n"
                f"{desc}\n\n"
                f"Siren coordinator don confirm am. We don alert your neighbours "
                f"for {lga}, we don tell emergency services.\n\n"
                f"Follow: {tracking_url}\n\n"
                f"Na because you subscribe to {lga} alerts you dey see this.\n"
                f"Reply STOP {lga} to comot."
            )
        return (
            f"\U0001f6a8 SIREN ALERT — {lga}\n\n"
            f"{incident_type_label} in {incident.zone_name}\n"
            f"Severity: {severity}\n\n"
            f"{desc}\n\n"
            f"Confirmed by a Siren coordinator. Your neighbours in {lga} have been "
            f"alerted and emergency services notified.\n\n"
            f"Track: {tracking_url}\n\n"
            f"You're receiving this because you subscribed to {lga} alerts.\n"
            f"Reply STOP {lga} to unsubscribe."
        )

    # BRD §5.1.3: LGA alerts are business-initiated, so they need an approved
    # template. Without one, delivery only works for subscribers who happen to
    # have messaged us in the last 24h — i.e. almost nobody during a pilot.
    template_sid = getattr(settings, 'TWILIO_TEMPLATE_ZONE_ALERT', '')
    if not template_sid:
        logger.warning(
            "notify_location_subscribers: TWILIO_TEMPLATE_ZONE_ALERT is not set; "
            "falling back to free-form text for incident %s. Subscribers outside "
            "the 24h WhatsApp service window will NOT receive this alert.",
            incident_id,
        )

    sent = 0
    for sub in subscribers:
        # Dedup: one alert per subscription+incident (unique_together).
        # The create MUST be in its own atomic block: a caught IntegrityError
        # otherwise poisons the surrounding transaction, so every remaining
        # subscriber silently fails to be alerted whenever this task runs
        # inside one (e.g. CELERY_TASK_ALWAYS_EAGER during a request).
        try:
            with transaction.atomic():
                LGASubscriptionAlert.objects.create(subscription=sub, incident=incident)
        except IntegrityError:
            continue

        phone = sub.whatsapp_number
        if not phone:
            continue

        # Ensure number has whatsapp: prefix for Twilio
        if not phone.startswith('whatsapp:'):
            phone = f'whatsapp:{phone}'

        try:
            if template_sid:
                # Business-initiated: must be an approved template or Meta
                # rejects it for anyone outside the 24h service window.
                # Template placeholders: {{1}} type, {{2}} LGA, {{3}} severity,
                # {{4}} tracking URL.
                send_whatsapp_template.delay(phone, template_sid, {
                    "1": incident_type_label,
                    "2": lga,
                    "3": severity,
                    "4": tracking_url,
                })
            else:
                send_whatsapp_text.delay(phone, _alert_message(get_language(phone)))
            sent += 1
        except Exception as e:
            logger.error(
                "notify_location_subscribers: failed to send to %s: %s", phone, e
            )

    logger.info(
        "notify_location_subscribers: sent %d alerts for LGA '%s' (incident %s)",
        sent, lga, incident_id,
    )


def normalize_lga_name(zone_name):
    """
    Normalize a zone name to a canonical Lagos LGA name.
    Returns the canonical name, or the title-cased zone_name if unrecognized.
    """
    if not zone_name:
        return None

    zone_lower = zone_name.lower().strip()

    LGA_MAP = {
        'surulere': 'Surulere',
        'yaba': 'Lagos Mainland',
        'apapa': 'Apapa',
        'mushin': 'Mushin',
        'ikeja': 'Ikeja',
        'agege': 'Agege',
        'alimosho': 'Alimosho',
        'oshodi': 'Oshodi-Isolo',
        'isolo': 'Oshodi-Isolo',
        'oshodi-isolo': 'Oshodi-Isolo',
        'somolu': 'Somolu',
        'shomolu': 'Shomolu',
        'kosofe': 'Kosofe',
        'gbagada': 'Kosofe',
        'ajeromi': 'Ajeromi-Ifelodun',
        'ajeromi-ifelodun': 'Ajeromi-Ifelodun',
        'amuwo': 'Amuwo-Odofin',
        'amuwo-odofin': 'Amuwo-Odofin',
        'festac': 'Amuwo-Odofin',
        'ikorodu': 'Ikorodu',
        'epe': 'Epe',
        'badagry': 'Badagry',
        'ojo': 'Ojo',
        'ifako': 'Ifako-Ijaiye',
        'ijaiye': 'Ifako-Ijaiye',
        'ifako-ijaiye': 'Ifako-Ijaiye',
        # Eti-Osa aliases
        'victoria island': 'Eti-Osa',
        'v.i.': 'Eti-Osa',
        'vi': 'Eti-Osa',
        'lekki': 'Eti-Osa',
        'ikoyi': 'Eti-Osa',
        'ajah': 'Eti-Osa',
        'eti-osa': 'Eti-Osa',
        'eti osa': 'Eti-Osa',
        'ibeju-lekki': 'Ibeju-Lekki',
        'ibeju lekki': 'Ibeju-Lekki',
        # Lagos Island
        'lagos island': 'Lagos Island',
        'cms': 'Lagos Island',
        'marina': 'Lagos Island',
        'lagos mainland': 'Lagos Mainland',
    }

    # Exact match
    if zone_lower in LGA_MAP:
        return LGA_MAP[zone_lower]

    # Partial match (e.g. "Surulere area" → "Surulere")
    for alias, canonical in LGA_MAP.items():
        if alias in zone_lower:
            return canonical

    # Return title-cased original so unrecognized zones still get logged
    return zone_name.title()


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
