"""
Inbound WhatsApp message router.
All messages from Twilio come through route_inbound().
"""
import hashlib
import logging

from django.core.cache import cache

from apps.incidents.models import Incident, VouchRecord
from apps.whatsapp import templates as tmpl
from apps.whatsapp.tasks import send_whatsapp_text
from apps.incidents.tasks import verify_incident_ai

logger = logging.getLogger(__name__)

ONBOARDING_TTL = 600  # 10 minutes

# -- Emergency intent detection ------------------------------------------------

EMERGENCY_KEYWORDS = {
    # English
    'fire', 'flood', 'accident', 'collapse', 'explosion', 'drowning',
    'hazard', 'help', 'emergency', 'sos',
    # Pidgin
    'wahala',
    # Common Lagos terms
    'wire', 'tanker', 'nepa', 'ekedc',
    # Yoruba
    'ina',   # fire
    # Hausa
    'wuta', 'hatsari',  # fire, accident
}

SINGLE_WORD_TYPE_MAP = {
    'fire': 'FIRE', 'ina': 'FIRE', 'wuta': 'FIRE',
    'flood': 'FLOOD',
    'accident': 'RTA', 'hatsari': 'RTA',
    'collapse': 'COLLAPSE',
    'explosion': 'EXPLOSION',
    'drowning': 'DROWNING',
    'wire': 'HAZARD', 'nepa': 'HAZARD', 'ekedc': 'HAZARD',
    'hazard': 'HAZARD',
}


def detect_emergency_intent(body):
    """
    Quick check: does the message contain any emergency keyword?
    Returns (has_intent: bool, suggested_type: str or None)
    """
    words = set(body.lower().split())
    for word in words:
        # Strip punctuation from word edges
        clean = word.strip('!?.,;:')
        if clean in EMERGENCY_KEYWORDS:
            suggested_type = SINGLE_WORD_TYPE_MAP.get(clean, '')
            return True, suggested_type
    return False, None


# -- Entry point ---------------------------------------------------------------

def route_inbound(from_number, body, media_urls, location):
    body_upper = body.strip().upper()

    if body_upper in ['YES', 'NO', 'ONSCENE', 'DONE', 'HELP']:
        return handle_responder_reply(from_number, body_upper)

    if body_upper in ['ACCEPT', 'DECLINE', 'CALL']:
        return handle_org_reply(from_number, body_upper)

    if body_upper == 'RESPONDER':
        return start_responder_registration(from_number)
    if body_upper == 'REGISTER ORG':
        return start_org_registration(from_number)

    # LGA Guardian Mode subscription commands
    if body_upper.startswith('WATCH '):
        handle_subscribe_command(from_number, body[6:].strip())
        return
    if body_upper == 'WATCH':
        send_available_lgas(from_number)
        return
    # v8 §6 US-2: LIST returns the sender's active LGA subscriptions.
    if body_upper in ('MY ALERTS', 'LIST'):
        return show_subscriptions(from_number)

    # STOP <LGA or label>: try LGA unsubscribe first, fall back to COMMUTE label
    if body_upper.startswith('STOP '):
        return handle_unsubscribe_command(from_number, body[5:].strip())
    if body_upper == 'STOP':
        return handle_stop_command(from_number, body)

    if body_upper.startswith('VOUCH'):
        return handle_vouch_command(from_number, body)

    # v5 new commands
    if body_upper in ['POINT', 'COMMUTE']:
        return handle_subscription_type_choice(from_number, body_upper)
    if body_upper == 'MY COMMUTE':
        return show_commute_briefing(from_number)
    if body_upper == 'MY IMPACT':
        return send_impact_link(from_number)
    if body_upper == 'NEED RIDE':
        return handle_need_ride(from_number)

    if location and location.get('latitude'):
        return handle_location_share(from_number, location, body)

    if is_onboarding(from_number):
        return handle_onboarding_step(from_number, body)

    # v7: Fast-path for non-emergency short messages
    has_intent, _ = detect_emergency_intent(body)
    if not has_intent and len(body.split()) <= 3:
        # Short message with zero emergency indicators -- send welcome
        send_whatsapp_text.delay(
            from_number,
            "Welcome to Siren NG -- Lagos emergency coordination.\n\n"
            "To report an emergency, describe what you see.\n"
            "Example: \"Fire at Balogun market, smoke everywhere\"\n\n"
            "Or send your location with a description."
        )
        return

    return create_incident_from_message(from_number, body, media_urls, location)


# -- Incident creation ---------------------------------------------------------

def create_incident_from_message(from_number, body, media_urls, location):
    phone_hash = hashlib.sha256(from_number.encode()).hexdigest()

    kwargs = dict(
        source='WHATSAPP',
        reporter_hash=phone_hash,
        reporter_phone=from_number,
        description=body,
        media_urls=media_urls or [],
        status='DETECTED',
    )
    if location:
        kwargs['location_lat'] = location.get('latitude')
        kwargs['location_lng'] = location.get('longitude')

    incident = Incident.objects.create(**kwargs)
    verify_incident_ai.delay(str(incident.id))
    if media_urls:
        from apps.whatsapp.tasks import process_whatsapp_media
        process_whatsapp_media.delay(str(incident.id), media_urls)
    send_whatsapp_text.delay(from_number, tmpl.received_ack())
    return incident


# -- Vouch ---------------------------------------------------------------------

def handle_vouch_command(from_number, body):
    parts = body.strip().split(None, 1)
    if len(parts) < 2:
        send_whatsapp_text.delay(
            from_number,
            "To vouch for an incident, reply: VOUCH [incident-id]"
        )
        return

    incident_ref = parts[1].strip()
    incident = None
    try:
        incident = Incident.objects.get(id=incident_ref)
    except (Incident.DoesNotExist, Exception):
        try:
            incident = Incident.objects.filter(
                id__startswith=incident_ref[:8]
            ).first()
        except Exception:
            pass

    if not incident:
        send_whatsapp_text.delay(
            from_number,
            f"Incident '{incident_ref}' not found. Check the ID and try again."
        )
        return

    session_hash = hashlib.sha256(
        (from_number + str(incident.id)).encode()
    ).hexdigest()

    try:
        VouchRecord.objects.create(
            incident=incident,
            session_hash=session_hash,
            source='WHATSAPP',
        )
        incident.vouch_count += 1
        incident.save(update_fields=['vouch_count'])
    except Exception:
        pass  # Already vouched -- that is fine

    send_whatsapp_text.delay(from_number, tmpl.vouch_confirmed(incident))


# -- Responder replies ---------------------------------------------------------

def handle_responder_reply(from_number, command):
    try:
        from apps.responders.models import Responder, ResponderDispatch
        from django.utils import timezone

        phone_hash = hashlib.sha256(from_number.encode()).hexdigest()
        try:
            responder = Responder.objects.get(phone_hash=phone_hash)
        except Responder.DoesNotExist:
            send_whatsapp_text.delay(
                from_number,
                "You are not registered as a Siren responder. Reply RESPONDER to register."
            )
            return

        dispatch = (
            ResponderDispatch.objects
            .filter(responder=responder, accepted__isnull=True)
            .select_related('incident')
            .order_by('-notified_at')
            .first()
        )

        if command == 'HELP':
            active_dispatch = (
                ResponderDispatch.objects
                .filter(responder=responder, accepted=True, completed_at__isnull=True)
                .select_related('incident')
                .order_by('-notified_at')
                .first()
            )
            if active_dispatch:
                incident = active_dispatch.incident
                send_whatsapp_text.delay(
                    from_number,
                    f"Backup request noted for {incident.incident_type or 'incident'} "
                    f"at {incident.address_text or incident.zone_name}.\n\n"
                    "Additional responders are being notified."
                )
                from apps.responders.tasks import notify_nearest_responders
                notify_nearest_responders.delay(
                    str(incident.id),
                    exclude_ids=[str(responder.id)]
                )
            return

        if not dispatch:
            send_whatsapp_text.delay(
                from_number,
                "No pending dispatch found. You may have already responded."
            )
            return

        incident = dispatch.incident

        if command == 'YES':
            dispatch.accepted = True
            dispatch.save(update_fields=['accepted'])
            incident.status = 'RESPONDING'
            incident.save(update_fields=['status'])
            send_whatsapp_text.delay(
                from_number, tmpl.responder_directions(responder, incident)
            )

        elif command == 'NO':
            dispatch.accepted = False
            dispatch.save(update_fields=['accepted'])
            from apps.responders.tasks import notify_nearest_responders
            notify_nearest_responders.delay(
                str(incident.id),
                exclude_ids=[str(responder.id)]
            )

        elif command == 'ONSCENE':
            dispatch.on_scene_at = timezone.now()
            dispatch.save(update_fields=['on_scene_at'])
            send_whatsapp_text.delay(
                from_number, tmpl.responder_onscene_ack(responder, incident)
            )

        elif command == 'DONE':
            dispatch.completed_at = timezone.now()
            dispatch.save(update_fields=['completed_at'])
            responder.total_responses += 1
            responder.save(update_fields=['total_responses'])
            send_whatsapp_text.delay(
                from_number, tmpl.responder_done_ack(incident)
            )

    except Exception as exc:
        logger.exception("handle_responder_reply error: %s", exc)


# -- Org replies ---------------------------------------------------------------

def handle_org_reply(from_number, command):
    try:
        from apps.organisations.models import Organisation

        org = Organisation.objects.filter(
            contact_whatsapp=from_number
        ).first()

        if not org:
            send_whatsapp_text.delay(
                from_number,
                "Your organisation is not registered with Siren. Reply REGISTER ORG to register."
            )
            return

        if command == 'ACCEPT':
            org.total_responses += 1
            org.save(update_fields=['total_responses'])
            incident = Incident.objects.filter(
                status__in=['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED']
            ).order_by('-created_at').first()
            if incident:
                send_whatsapp_text.delay(
                    from_number, tmpl.org_accept_ack(org, incident)
                )
            else:
                send_whatsapp_text.delay(
                    from_number, "Response noted. Thank you."
                )

        elif command == 'DECLINE':
            send_whatsapp_text.delay(
                from_number,
                "Understood. We will check back with you when capacity is available."
            )

        elif command == 'CALL':
            send_whatsapp_text.delay(
                from_number,
                "For immediate coordination, call Lagos State Emergency: 767\n\n"
                "Siren admin has been alerted."
            )

    except Exception as exc:
        logger.exception("handle_org_reply error: %s", exc)


# -- Registration --------------------------------------------------------------

def start_responder_registration(from_number):
    send_whatsapp_text.delay(from_number, tmpl.registration_instructions('responder'))


def start_org_registration(from_number):
    send_whatsapp_text.delay(from_number, tmpl.registration_instructions('org'))


# -- Location share ------------------------------------------------------------

def handle_location_share(from_number, location, body):
    if is_onboarding(from_number):
        state = get_onboarding_state(from_number)
        step = state.get('step') if state else None

        if step == 'location':
            state['lat'] = location.get('latitude')
            state['lng'] = location.get('longitude')
            state['step'] = 'radius'
            set_onboarding_state(from_number, state)
            send_whatsapp_text.delay(from_number, tmpl.watch_ask_radius())
            return

        if step == 'awaiting_office_location':
            state['office_lat'] = location.get('latitude')
            state['office_lng'] = location.get('longitude')
            _save_commute_subscription(from_number, state)
            return

    # Not onboarding — delegate to location message handler (BRD 11.16)
    handle_location_message(from_number, location.get('latitude'), location.get('longitude'))


# -- LGA Guardian Mode commands ------------------------------------------------

AVAILABLE_LGAS = [
    'Agege', 'Ajeromi-Ifelodun', 'Alimosho', 'Amuwo-Odofin', 'Apapa',
    'Badagry', 'Epe', 'Eti-Osa', 'Ibeju-Lekki', 'Ifako-Ijaiye',
    'Ikorodu', 'Ikeja', 'Kosofe', 'Lagos Island', 'Lagos Mainland',
    'Mushin', 'Ojo', 'Oshodi-Isolo', 'Shomolu', 'Somolu', 'Surulere',
]


def send_available_lgas(from_number):
    """Reply with the list of Lagos LGAs a user can subscribe to."""
    lga_list = '\n'.join(f'• {lga}' for lga in AVAILABLE_LGAS)
    send_whatsapp_text.delay(
        from_number,
        f"Guardian Mode — Lagos LGA Alerts\n\n"
        f"To subscribe to an LGA, text:\n"
        f"WATCH <LGA name>\n\n"
        f"Example: WATCH Surulere\n\n"
        f"Available LGAs:\n{lga_list}\n\n"
        f"To unsubscribe: STOP <LGA name>"
    )


def handle_subscribe_command(from_number, lga):
    """Subscribe the sender to Guardian Mode alerts for one or more Lagos LGAs.

    v8 §6 US-2: accepts a single LGA ("WATCH Surulere") or a comma-separated
    list ("WATCH Surulere, Yaba"). Each term is normalised through the alias
    table (Yaba→Lagos Mainland, Isolo→Oshodi-Isolo, VI/Lekki→Eti-Osa, ...).
    """
    from apps.subscriptions.tasks import normalize_lga_name
    from apps.subscriptions.models import LGASubscription
    from django.contrib.auth import get_user_model

    if not lga:
        send_available_lgas(from_number)
        return

    terms = [t.strip() for t in lga.split(',') if t.strip()]
    if not terms:
        send_available_lgas(from_number)
        return

    User = get_user_model()
    user, _ = User.objects.get_or_create(username=from_number)

    subscribed, already, unknown, seen = [], [], [], set()
    for term in terms:
        normalized = normalize_lga_name(term)
        if not normalized or normalized not in AVAILABLE_LGAS:
            unknown.append(term)
            continue
        if normalized in seen:
            continue
        seen.add(normalized)

        sub, created = LGASubscription.objects.get_or_create(
            user=user,
            lga=normalized,
            defaults={'is_active': True, 'whatsapp_number': from_number},
        )
        if not created and sub.is_active:
            already.append(normalized)
        else:
            if not created:
                sub.is_active = True
                sub.whatsapp_number = from_number
                sub.save(update_fields=['is_active', 'whatsapp_number', 'updated_at'])
            subscribed.append(normalized)

    lines = []
    if subscribed:
        where = "these areas" if len(subscribed) > 1 else subscribed[0]
        lines.append(
            "Subscribed to alerts for: " + ", ".join(subscribed) + ".\n"
            "You will receive a WhatsApp message whenever an emergency is "
            f"verified in {where}."
        )
    if already:
        lines.append("Already subscribed to: " + ", ".join(already) + ".")
    if unknown:
        lines.append(
            "Not recognised: " + ", ".join(unknown) + ".\n"
            "Text WATCH to see the full list of Lagos LGAs."
        )
    if subscribed or already:
        lines.append("To unsubscribe from an area: STOP <LGA name>")

    send_whatsapp_text.delay(from_number, "\n\n".join(lines))


def handle_unsubscribe_command(from_number, term):
    """
    Unsubscribe from a Guardian Mode LGA alert.
    Falls back to the old COMMUTE label stop if no LGA subscription is found.
    """
    from apps.subscriptions.tasks import normalize_lga_name
    from apps.subscriptions.models import LGASubscription
    from django.contrib.auth import get_user_model

    normalized = normalize_lga_name(term)
    if normalized:
        User = get_user_model()
        try:
            user = User.objects.get(username=from_number)
            sub = LGASubscription.objects.filter(
                user=user, lga=normalized, is_active=True
            ).first()
            if sub:
                sub.is_active = False
                sub.save(update_fields=['is_active', 'updated_at'])
                send_whatsapp_text.delay(
                    from_number,
                    f"Unsubscribed from {normalized} alerts.\n\n"
                    f"Text WATCH {normalized} to resubscribe."
                )
                return
        except Exception:
            pass

    # No LGA match — fall back to COMMUTE label stop
    handle_stop_command(from_number, f'STOP {term}')


# -- Location message handler (BRD 11.16) --------------------------------------

def handle_location_message(from_number, latitude, longitude):
    """
    Process WhatsApp location messages (static or live location sharing).

    Associates location with the user's most recent active incident.
    Only saves the first location received to prevent drift for static incidents.

    Returns:
        bool: True if location was saved, False if ignored
    """
    from django.utils import timezone
    from datetime import timedelta

    cutoff_time = timezone.now() - timedelta(minutes=10)
    phone_hash = hashlib.sha256(from_number.encode()).hexdigest()

    try:
        recent_incident = Incident.objects.filter(
            reporter_hash=phone_hash,
            status__in=['DETECTED', 'VERIFYING', 'VERIFIED'],
            created_at__gte=cutoff_time,
        ).order_by('-created_at').first()
    except Exception as e:
        logger.error("handle_location_message: Error querying incidents: %s", e)
        return False

    if not recent_incident:
        logger.info(
            "handle_location_message: No recent incident found for %s", from_number
        )
        return False

    if recent_incident.location_lat and recent_incident.location_lng:
        logger.info(
            "handle_location_message: Location ignored for incident %s: coordinates already set",
            recent_incident.id,
        )
        return False

    try:
        recent_incident.location_lat = float(latitude)
        recent_incident.location_lng = float(longitude)
        recent_incident.save(update_fields=['location_lat', 'location_lng', 'updated_at'])

        logger.info(
            "handle_location_message: Location saved for incident %s: %s, %s",
            recent_incident.id, latitude, longitude,
        )

        send_whatsapp_text.delay(from_number, "\U0001f4cd Location saved. Thank you.")
        return True

    except (ValueError, TypeError) as e:
        logger.error(
            "handle_location_message: Invalid coordinates for %s: lat=%s, lng=%s, error=%s",
            recent_incident.id, latitude, longitude, e,
        )
        return False
    except Exception as e:
        logger.error(
            "handle_location_message: Failed to save location for %s: %s",
            recent_incident.id, e,
        )
        return False


# -- Subscription (WATCH) flow -------------------------------------------------

def start_subscription_flow(from_number):
    set_onboarding_state(from_number, {'flow': 'watch', 'step': 'label'})
    send_whatsapp_text.delay(from_number, tmpl.watch_ask_label())


def is_onboarding(from_number):
    return get_onboarding_state(from_number) is not None


def get_onboarding_state(from_number):
    return cache.get(f'onboarding:{from_number}')


def set_onboarding_state(from_number, state):
    cache.set(f'onboarding:{from_number}', state, ONBOARDING_TTL)


def clear_onboarding_state(from_number):
    cache.delete(f'onboarding:{from_number}')


def handle_onboarding_step(from_number, body):
    state = get_onboarding_state(from_number)
    if not state:
        return
    flow = state.get('flow')
    if flow == 'watch':
        _handle_watch_step(from_number, body, state)


LOCATION_TYPE_MAP = {
    '1': 'HOME', '2': 'SCHOOL', '3': 'LAND',
    '4': 'OFFICE', '5': 'FAMILY', '6': 'OTHER',
}

RADIUS_MAP = {
    '1': 0.5, '2': 1.0, '3': 2.0, '4': 5.0,
}


def _handle_watch_step(from_number, body, state):
    step = state.get('step')

    if step == 'label':
        label = body.strip()[:200]
        if not label:
            send_whatsapp_text.delay(from_number, "Please enter a name for this location.")
            return
        state['label'] = label
        state['step'] = 'type'
        set_onboarding_state(from_number, state)
        send_whatsapp_text.delay(from_number, tmpl.watch_ask_type(label))

    elif step == 'type':
        choice = body.strip()
        location_type = LOCATION_TYPE_MAP.get(choice)
        if not location_type:
            send_whatsapp_text.delay(
                from_number, "Please reply with a number 1-6."
            )
            return
        state['location_type'] = location_type
        state['step'] = 'location'
        set_onboarding_state(from_number, state)
        send_whatsapp_text.delay(
            from_number, tmpl.watch_ask_location(state['label'])
        )

    elif step == 'location':
        send_whatsapp_text.delay(
            from_number,
            "Please share the location using the WhatsApp location pin, not text.\n\n"
            "Tap the paperclip icon, select Location, then send."
        )

    elif step == 'radius':
        choice = body.strip()
        radius_km = RADIUS_MAP.get(choice)
        if not radius_km:
            send_whatsapp_text.delay(
                from_number, "Please reply with a number 1-4."
            )
            return

        import hashlib as _h
        from apps.subscriptions.models import LocationSubscription
        phone_hash = _h.sha256(from_number.encode()).hexdigest()

        label = state.get('label', 'My location')
        location_type = state.get('location_type', 'OTHER')
        lat = state.get('lat')
        lng = state.get('lng')

        if not lat or not lng:
            send_whatsapp_text.delay(
                from_number,
                "Location was not received. Please start again -- reply WATCH."
            )
            clear_onboarding_state(from_number)
            return

        LocationSubscription.objects.create(
            phone_hash=phone_hash,
            whatsapp_number=from_number,
            label=label,
            location_type=location_type,
            location_lat=lat,
            location_lng=lng,
            alert_radius_km=radius_km,
            subscription_type='POINT',
        )

        # v5: Ask if they want Guardian (POINT) or Commute Shield (COMMUTE)
        state['saved_label'] = label
        state['step'] = 'awaiting_subscription_type'
        set_onboarding_state(from_number, state)
        send_whatsapp_text.delay(from_number, tmpl.subscription_saved(label, location_type, radius_km))
        send_whatsapp_text.delay(from_number, tmpl.commute_type_question())

    elif step == 'awaiting_subscription_type':
        # Handled by route_inbound's POINT/COMMUTE check -- but catch stray text here
        send_whatsapp_text.delay(
            from_number,
            "Reply POINT to finish here, or COMMUTE to set up your daily route."
        )


def show_subscriptions(from_number):
    import hashlib as _h
    from apps.subscriptions.models import LocationSubscription

    phone_hash = _h.sha256(from_number.encode()).hexdigest()
    subs = list(LocationSubscription.objects.filter(phone_hash=phone_hash))
    send_whatsapp_text.delay(from_number, tmpl.show_subscriptions_message(subs))


def handle_stop_command(from_number, body):
    import hashlib as _h
    from apps.subscriptions.models import LocationSubscription

    parts = body.strip().split(None, 1)
    if len(parts) < 2:
        send_whatsapp_text.delay(
            from_number,
            "To stop alerts, reply: STOP [location name]\nExample: STOP Timi school"
        )
        return

    label = parts[1].strip()
    phone_hash = _h.sha256(from_number.encode()).hexdigest()

    sub = LocationSubscription.objects.filter(
        phone_hash=phone_hash,
        label__iexact=label,
        is_active=True,
    ).first()

    if not sub:
        send_whatsapp_text.delay(from_number, tmpl.stop_not_found(label))
        return

    sub.is_active = False
    sub.save(update_fields=['is_active'])
    send_whatsapp_text.delay(from_number, tmpl.stop_confirmed(label))


# -- v5 New command handlers ---------------------------------------------------

def handle_subscription_type_choice(from_number, choice):
    """
    Called when user replies POINT or COMMUTE after saving first location.
    POINT: subscription already saved as POINT. Send done message.
    COMMUTE: ask for home pin then office pin.
    """
    state = get_onboarding_state(from_number)

    if choice == 'POINT':
        clear_onboarding_state(from_number)
        send_whatsapp_text.delay(
            from_number,
            "Guardian Mode is active.\n\n"
            "You will receive alerts for incidents near your saved location.\n"
            "Reply WATCH to add more locations.\n"
            "Reply MY IMPACT to see your community impact."
        )
        return

    # COMMUTE
    if state:
        state['step'] = 'awaiting_office_location'
        state['flow'] = 'watch'
    else:
        state = {'flow': 'watch', 'step': 'awaiting_office_location'}
    set_onboarding_state(from_number, state)
    send_whatsapp_text.delay(from_number, tmpl.commute_setup_home_prompt())


def _save_commute_subscription(from_number, state):
    """Save COMMUTE subscription once both home and office pins are collected."""
    import hashlib as _h
    from apps.subscriptions.models import LocationSubscription

    office_lat = state.get('office_lat')
    office_lng = state.get('office_lng')
    home_lat = state.get('lat')
    home_lng = state.get('lng')

    if not home_lat or not home_lng:
        send_whatsapp_text.delay(
            from_number,
            "Home location missing. Please start again -- reply WATCH."
        )
        clear_onboarding_state(from_number)
        return

    phone_hash = _h.sha256(from_number.encode()).hexdigest()
    label = state.get('label', 'My commute')
    location_type = state.get('location_type', 'HOME')

    # Update the POINT sub to COMMUTE, or create a new one
    sub = LocationSubscription.objects.filter(
        phone_hash=phone_hash,
        label=label,
        subscription_type='POINT',
    ).first()

    if sub:
        sub.subscription_type = 'COMMUTE'
        sub.office_lat = office_lat
        sub.office_lng = office_lng
        sub.peak_only = True
        sub.save()
    else:
        sub = LocationSubscription.objects.create(
            phone_hash=phone_hash,
            whatsapp_number=from_number,
            label=label,
            location_type=location_type,
            location_lat=home_lat,
            location_lng=home_lng,
            office_lat=office_lat,
            office_lng=office_lng,
            subscription_type='COMMUTE',
            peak_only=True,
        )

    clear_onboarding_state(from_number)
    send_whatsapp_text.delay(from_number, tmpl.commute_shield_saved(sub))


def show_commute_briefing(from_number):
    """Fetch current commute status and send to user."""
    import hashlib as _h
    from apps.subscriptions.models import LocationSubscription
    from apps.incidents.models import Incident
    from utils.distance import point_to_line_distance
    from django.utils import timezone
    from datetime import timedelta

    phone_hash = _h.sha256(from_number.encode()).hexdigest()
    sub = LocationSubscription.objects.filter(
        phone_hash=phone_hash,
        subscription_type='COMMUTE',
        is_active=True,
    ).first()

    if not sub:
        send_whatsapp_text.delay(
            from_number,
            "You have no active Commute Shield.\n\n"
            "Reply WATCH then COMMUTE to set one up."
        )
        return

    cutoff = timezone.now() - timedelta(hours=24)
    recent_incidents = Incident.objects.filter(
        status__in=['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED'],
        created_at__gte=cutoff,
        incident_type__in=['HAZARD', 'RTA', 'FLOOD'],
    ).exclude(location_lat=None)

    corridor_incidents = []
    for inc in recent_incidents:
        if sub.office_lat and sub.office_lng:
            dist = point_to_line_distance(
                inc.location_lat, inc.location_lng,
                sub.location_lat, sub.location_lng,
                sub.office_lat, sub.office_lng,
            )
            if dist <= sub.commute_buffer_km:
                corridor_incidents.append((inc, dist))

    from apps.subscriptions.tasks import _build_briefing_message
    import pytz
    from django.utils import timezone as tz
    lagos_tz = pytz.timezone('Africa/Lagos')
    hour = tz.now().astimezone(lagos_tz).hour
    message = _build_briefing_message(sub, corridor_incidents, hour < 12)
    send_whatsapp_text.delay(from_number, message)


def send_impact_link(from_number):
    """Send the user a link to their My Impact page."""
    import hashlib as _h
    phone_hash = _h.sha256(from_number.encode()).hexdigest()
    send_whatsapp_text.delay(from_number, tmpl.my_impact_link(phone_hash))


def handle_need_ride(from_number):
    """
    Find the most recent SubscriptionAlert for this number.
    Create a TRANSPORT ResourceClaim. Send response.
    """
    import hashlib as _h
    from apps.subscriptions.models import LocationSubscription, SubscriptionAlert

    phone_hash = _h.sha256(from_number.encode()).hexdigest()
    subs = LocationSubscription.objects.filter(phone_hash=phone_hash)

    latest_alert = (
        SubscriptionAlert.objects
        .filter(subscription__in=subs)
        .select_related('incident')
        .order_by('-sent_at')
        .first()
    )

    if not latest_alert:
        send_whatsapp_text.delay(
            from_number,
            "No recent incidents found near your saved locations.\n\n"
            "Reply WATCH to save your locations and get alerts."
        )
        return

    incident = latest_alert.incident

    # v5: Create the resource claim
    from apps.resources.models import ResourceItem, ResourceClaim
    resource = ResourceItem.objects.create(
        incident=incident,
        category='TRANSPORT',
        label=f"Ride for {from_number[-4:]}",
        status='NEEDED',
        suggested_by_hash=phone_hash,
        suggested_via='WHATSAPP'
    )
    ResourceClaim.objects.create(
        resource=resource,
        claimer_hash=phone_hash,
        claimer_phone=from_number
    )

    send_whatsapp_text.delay(
        from_number,
        f"Noted -- looking for transport near you on the incident board.\n\n"
        f"See who is offering: {tmpl.SITE_URL}/track/{incident.id}"
    )
