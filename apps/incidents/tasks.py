import json
import logging
import re
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

# The AI sees attacker-controlled text, so everything it returns is UNTRUSTED
# INPUT — never a source of authority. We validate it against a strict schema
# and drop anything unexpected. In particular the model cannot grant itself a
# privileged outcome: keys like "verified"/"status" are simply not read.
VALID_INCIDENT_TYPES = {
    'FIRE', 'FLOOD', 'COLLAPSE', 'RTA', 'EXPLOSION', 'DROWNING', 'HAZARD',
}
VALID_SEVERITIES = {'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'}
MAX_AI_TEXT_FIELD = 120


def _clamp_unit(value, default=0.0):
    """Coerce to a float in [0.0, 1.0]; fall back to `default`."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    if f != f:  # NaN
        return default
    return max(0.0, min(1.0, f))


def _validate_ai_result(raw) -> dict:
    """Project raw model output onto a strict, safe schema."""
    if not isinstance(raw, dict):
        raise ValueError("AI response was not a JSON object")

    incident_type = str(raw.get('incident_type') or '').strip().upper()
    severity = str(raw.get('severity') or '').strip().upper()
    zone = str(raw.get('zone_name') or '').strip()[:MAX_AI_TEXT_FIELD]
    reason = str(raw.get('rejection_reason') or '').strip()[:MAX_AI_TEXT_FIELD]

    return {
        'eligible': bool(raw.get('eligible')),
        'incident_type': incident_type if incident_type in VALID_INCIDENT_TYPES else '',
        'severity': severity if severity in VALID_SEVERITIES else 'MEDIUM',
        'ai_confidence': _clamp_unit(raw.get('ai_confidence')),
        'fraud_score': _clamp_unit(raw.get('fraud_score')),
        'is_infrastructure': bool(raw.get('is_infrastructure')),
        'zone_name': zone,
        'rejection_reason': reason,
    }


def _call_ai(prompt: str) -> dict:
    """
    Calls the configured AI provider (groq or anthropic) and returns parsed JSON.
    Switch providers by setting AI_PROVIDER in .env.
    """
    provider = getattr(settings, 'AI_PROVIDER', 'anthropic')

    if provider == 'groq':
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            max_tokens=1024,
            timeout=30,
        )
        text = completion.choices[0].message.content.strip()
    else:
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}],
            timeout=30,
        )
        text = message.content[0].text.strip()

    text = re.sub(r'```json|```', '', text).strip()
    return json.loads(text)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def verify_incident_ai(self, incident_id: str):
    """
    Calls AI to classify and verify an incident.
    Updates status. Triggers all downstream notifications if VERIFIED.
    """
    from apps.incidents.models import Incident

    incident = Incident.objects.get(id=incident_id)

    # v5: Extended prompt to detect infrastructure hazards
    # v7.3: Added zone_name extraction with Lagos LGA mapping
    prompt = f"""You are an emergency verification system for Lagos, Nigeria.
Analyse this report and respond ONLY with valid JSON. No markdown. No explanation.

--- USER INPUT ---
Report: {incident.description[:2000]}
Location text: {incident.address_text[:300]}
--- END USER INPUT ---

IMPORTANT CONTEXT:
- Reports come from Lagos residents via WhatsApp. They are often short and informal.
- A neighbourhood name, market name, bus stop, or street is sufficient location detail.
- Do NOT require GPS coordinates, casualty counts, or formal language.
- A single sentence like "fire at Yaba market" from a real Lagos location is eligible.
- Set eligible=true if the report describes a plausible real emergency, even if brief.
- Only set eligible=false if the report is clearly a test, joke, or completely unintelligible.
- fraud_score should be low (under 0.3) for any report with a recognisable Lagos location.

Return this exact JSON:
{{
  "eligible": true or false,
  "rejection_reason": "why rejected, or null if eligible",
  "incident_type": "FIRE|FLOOD|COLLAPSE|RTA|EXPLOSION|DROWNING|HAZARD or null",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "ai_confidence": 0.0 to 1.0,
  "fraud_score": 0.0 to 1.0,
  "is_infrastructure": true or false,
  "suggested_skills": ["list of skill codes"],
  "zone_name": "specific Lagos LGA name, or null if location cannot be determined",
  "reasoning": "one sentence"
}}

Only these types qualify: FIRE FLOOD COLLAPSE RTA EXPLOSION DROWNING HAZARD
fraud_score above 0.7 means the report looks fake.
is_infrastructure must be true if the report mentions transformer, wire, pole,
power line, NEPA, EKEDC, fallen cable, or electrical infrastructure of any kind.

CRITICAL RULES FOR zone_name:
- Return the SPECIFIC Lagos LGA (Local Government Area), never just "Lagos".
- Valid LGA names: Agege, Ajeromi-Ifelodun, Alimosho, Amuwo-Odofin, Apapa,
  Badagry, Epe, Eti-Osa, Ibeju-Lekki, Ifako-Ijaiye, Ikeja, Ikorodu, Kosofe,
  Lagos Island, Lagos Mainland, Mushin, Ojo, Oshodi-Isolo, Shomolu, Surulere.
- Neighbourhood to LGA mapping:
  Isolo, Oshodi, Ejigbo, Mafoluku, Cele → "Oshodi-Isolo"
  Yaba, Ebute Metta, Oyingbo, Adekunle, Otto, Sabo → "Lagos Mainland"
  Victoria Island, V.I., Ikoyi, Lekki Phase 1, Oniru → "Eti-Osa"
  Lekki-Ajah, Ajah, Sangotedo, Agungi, Chevron → "Eti-Osa"
  Surulere, Adeniran Ogunsanya, Bode Thomas, Aguda, Ojuelegba → "Surulere"
  Balogun, Idumota, Marina, Broad Street, Tinubu, Apongbon → "Lagos Island"
  Ikeja, Allen Avenue, Alausa, Oregun, Opebi, Maryland, Palmgrove → "Ikeja"
  Mushin, Idi-Oro, Ojuwoye, Palm Avenue, Ilasamaja → "Mushin"
  Agege, Pen Cinema, Oke-Odo, Mangoro, Abule-Egba → "Agege"
  Gbagada, Ogudu, Ojota, Ketu, Mile 12, Alapere → "Kosofe"
  Somolu, Shomolu, Bariga, Ilaje, Pedro → "Shomolu"
  Ajegunle, Olodi → "Ajeromi-Ifelodun"
  Apapa, Kirikiri, Tin Can → "Apapa"
  Festac, Satellite Town, Mile 2, Iba → "Amuwo-Odofin"
  Alimosho, Egbeda, Idimu, Igando, Akowonjo, Ipaja → "Alimosho"
  Ikorodu, Ijede, Imota, Bayeku, Agbowa → "Ikorodu"
  Badagry, Ajara, Seme → "Badagry"
  Epe, Lekki-Epe → "Epe"
  Ibeju, Lakowe, Abijo, Eleko → "Ibeju-Lekki"
  Ifako, Ijaiye, Agbado, Iju, Ogba → "Ifako-Ijaiye"
  Ojo, Alaba, Trade Fair, Okokomaiko → "Ojo"
  Third Mainland Bridge → "Lagos Mainland"
- If no recognisable location is mentioned, return null (not "Lagos")."""

    try:
        result = _validate_ai_result(_call_ai(prompt))
    except Exception as exc:
        raise self.retry(exc=exc)

    incident.ai_raw_response   = result
    incident.ai_confidence     = result.get('ai_confidence', 0.0)
    incident.fraud_score       = result.get('fraud_score', 0.0)
    incident.is_infrastructure = result.get('is_infrastructure', False)

    # v7.3: save AI-extracted LGA zone; reject generic "Lagos" fallbacks
    ai_zone = (result.get('zone_name') or '').strip()
    if ai_zone.lower() in ('lagos', 'lagos state', 'lagos nigeria', ''):
        ai_zone = ''
    if ai_zone:
        incident.zone_name = ai_zone

    if not result.get('eligible') or incident.fraud_score > 0.7:
        _transition(incident, 'REJECTED', 'AI', result.get('rejection_reason', ''))
        incident.save()
        _notify_rejected(incident, result.get('rejection_reason', ''))
        return

    incident.incident_type = result.get('incident_type', '')
    incident.severity      = result.get('severity', 'MEDIUM')
    incident.set_vouch_threshold()

    # v8: AI CLASSIFIES ONLY — it never auto-verifies and never broadcasts.
    # Every plausible report waits in the DETECTED queue for a human coordinator
    # to confirm (admin "Mark VERIFIED") before any alert is sent. This is the
    # Promise Invariant's companion rule: only human-verified incidents are ever
    # broadcast; an unverified report reaches no one but the coordinator.
    # (v8 BRD §5.1.2, §8.) Community vouching is HIDDEN in the MVP (returns at
    # Phase 1.5), so the AI no longer routes to VERIFYING.
    _transition(
        incident, 'DETECTED', 'AI',
        f'AI classified: {incident.incident_type or "?"}/{incident.severity}, '
        f'{incident.zone_name or "no LGA"}, confidence {incident.ai_confidence:.2f}. '
        f'Awaiting coordinator confirmation.'
    )
    incident.save()


def _transition(incident, new_status, actor, note=''):
    from apps.incidents.models import ResponseLog
    from apps.incidents.consumers import broadcast_update
    ResponseLog.objects.create(
        incident=incident, from_status=incident.status,
        to_status=new_status, actor=actor, note=note
    )
    incident.status = new_status
    try:
        broadcast_update(incident)  # Push to all WebSocket clients
    except Exception:
        pass  # Redis/channel layer unavailable -- do not block status save


def _post_verification_actions(incident):
    try:
        from apps.whatsapp.tasks import notify_reporter_verified, post_community_announcement
        logger.info(
            "verify_incident_ai: Incident %s verified. "
            "Triggering notify_reporter_verified for phone '%s'",
            incident.id,
            incident.reporter_phone or '<NO PHONE SET>',
        )
        notify_reporter_verified.delay(str(incident.id))
        post_community_announcement.delay(str(incident.id))
    except Exception as exc:
        logger.error(
            "_post_verification_actions: Failed to queue reporter notification "
            "for incident %s: %s",
            incident.id, exc,
        )

    # NOTE: each fan-out is isolated so one failure cannot cancel the others,
    # but failures are LOGGED AS ERRORS, never swallowed. A silently dropped
    # neighbour alert is an outright product failure for an emergency service
    # (BRD §9: alert delivery is a tracked pilot metric).
    try:
        from apps.responders.tasks import notify_nearest_responders
        if incident.severity in ['CRITICAL', 'HIGH', 'MEDIUM']:
            notify_nearest_responders.delay(str(incident.id))
    except Exception as exc:
        logger.error("_post_verification_actions: responder notify failed for %s: %s",
                     incident.id, exc, exc_info=True)

    try:
        from apps.organisations.tasks import notify_nearest_organisations
        notify_nearest_organisations.delay(str(incident.id))
    except Exception as exc:
        logger.error("_post_verification_actions: organisation notify failed for %s: %s",
                     incident.id, exc, exc_info=True)

    try:
        from apps.subscriptions.tasks import notify_location_subscribers
        notify_location_subscribers.delay(str(incident.id))
    except Exception as exc:
        # This is the core-loop alert. If it fails, neighbours are NOT told.
        logger.critical(
            "_post_verification_actions: LGA SUBSCRIBER ALERT FAILED for %s: %s",
            incident.id, exc, exc_info=True)

    # v8: Notify authorities. Every human-verified incident is forwarded to
    # LASEMA / official channels as a best-effort notification (§5.1.4, §5.4).
    try:
        forward_to_authorities.delay(str(incident.id))
    except Exception:
        pass

    # v5: Commute Shield -- OUT of the v8 MVP (§5.3, archived). Left in code but
    # disabled by default; set ENABLE_COMMUTE_SHIELD=true to re-enable.
    try:
        if getattr(settings, 'ENABLE_COMMUTE_SHIELD', False) and (
            incident.is_infrastructure or incident.incident_type in ['HAZARD', 'RTA', 'FLOOD']
        ):
            from apps.subscriptions.tasks import notify_commute_shield
            notify_commute_shield.delay(str(incident.id))
    except Exception:
        pass


def _is_safe_authority_url(url: str) -> bool:
    """Guard the operator-configured authority webhook against SSRF.

    The destination is set by an operator via env (never by a user), so this
    is defence-in-depth against misconfiguration being turned into an
    internal-network pivot: require https and refuse private, loopback,
    link-local and cloud-metadata addresses.
    """
    import ipaddress
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme.lower() != 'https' or not parsed.hostname:
        logger.error("forward_to_authorities: webhook must be an absolute https URL")
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror:
        logger.error("forward_to_authorities: webhook host does not resolve")
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast):
            logger.error("forward_to_authorities: webhook resolves to a non-public address")
            return False
    return True


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def forward_to_authorities(self, incident_id: str):
    """
    v8 §5.1.4 / §5.4 — Best-effort notification of a human-VERIFIED incident to
    LASEMA / official channels. This is a NOTIFICATION only: delivery status is
    logged for our audit but is NEVER surfaced to users as a promise (Promise
    Invariant, §8). No MoU is required or awaited.

    Configure any of:
      LASEMA_FORWARD_NUMBERS  comma-separated WhatsApp numbers (whatsapp:+234...)
      LASEMA_FORWARD_WEBHOOK  URL that accepts a JSON POST
    If neither is set, the intent is still logged so coverage can be audited.
    """
    from apps.incidents.models import Incident

    try:
        incident = Incident.objects.get(id=incident_id)
    except Incident.DoesNotExist:
        logger.error("forward_to_authorities: incident %s not found", incident_id)
        return

    zone = incident.zone_name or incident.address_text or 'Lagos'
    summary = (
        f"SIREN.NG — verified incident notification\n"
        f"Type: {incident.incident_type or 'Unclassified'}\n"
        f"Severity: {incident.severity}\n"
        f"LGA/Zone: {zone}\n"
        f"Location: {incident.address_text or 'see report'}\n"
        f"Reported: {incident.created_at:%Y-%m-%d %H:%M}\n"
        f"Ref: {incident.id}"
    )

    numbers = [n.strip() for n in getattr(settings, 'LASEMA_FORWARD_NUMBERS', '').split(',') if n.strip()]
    webhook = getattr(settings, 'LASEMA_FORWARD_WEBHOOK', '')
    delivered = False

    if numbers:
        try:
            from apps.whatsapp.tasks import send_whatsapp_text
            for num in numbers:
                dest = num if num.startswith('whatsapp:') else f'whatsapp:{num}'
                send_whatsapp_text.delay(dest, summary)
            delivered = True
        except Exception as exc:
            logger.error("forward_to_authorities: WhatsApp forward failed for %s: %s",
                         incident_id, exc)

    if webhook and _is_safe_authority_url(webhook):
        try:
            import requests
            requests.post(
                webhook,
                json={
                    'ref': str(incident.id),
                    'type': incident.incident_type,
                    'severity': incident.severity,
                    'lga': zone,
                    'address_text': incident.address_text,
                    'reported_at': incident.created_at.isoformat(),
                },
                timeout=10,
            )
            delivered = True
        except Exception as exc:
            logger.error("forward_to_authorities: webhook forward failed for %s: %s",
                         incident_id, exc)

    note = ('Forwarded to authorities (best-effort).' if delivered
            else 'Authority forward attempted — no channel configured; logged for audit.')
    try:
        # Only advance the lifecycle from VERIFIED so we never clobber a
        # concurrent RESOLVED/REJECTED transition.
        if incident.status == 'VERIFIED':
            _transition(incident, 'AGENCY_NOTIFIED', 'system', note)
            incident.save(update_fields=['status'])
        else:
            from apps.incidents.models import ResponseLog
            ResponseLog.objects.create(
                incident=incident, from_status=incident.status,
                to_status=incident.status, actor='system', note=note
            )
    except Exception:
        logger.info("forward_to_authorities: %s — %s", incident_id, note)


def _notify_rejected(incident, reason):
    try:
        from apps.whatsapp.tasks import notify_reporter_rejected
        notify_reporter_rejected.delay(str(incident.id), reason or '')
    except Exception:
        pass


def _notify_verifying(incident):
    try:
        from apps.whatsapp.tasks import notify_reporter_verifying
        notify_reporter_verifying.delay(str(incident.id))
    except Exception:
        pass


@shared_task
def check_verifying_escalation():
    """
    Runs every 5 minutes. Escalates VERIFYING incidents that have enough vouches
    or that have been waiting too long.
    """
    from apps.incidents.models import Incident
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(hours=2)

    for incident in Incident.objects.filter(status='VERIFYING'):
        if incident.vouch_count >= incident.vouch_threshold:
            _transition(incident, 'VERIFIED', 'community',
                        f'Escalated: {incident.vouch_count} vouches reached threshold')
            incident.save()
            _post_verification_actions(incident)
        elif incident.created_at < cutoff:
            _transition(incident, 'REJECTED', 'AI', 'Insufficient vouches after 2 hours')
            incident.save()
