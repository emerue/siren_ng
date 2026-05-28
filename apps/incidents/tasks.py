import json
import logging
import re
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


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
        )
        text = completion.choices[0].message.content.strip()
    else:
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}]
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
Report: {incident.description}
Location text: {incident.address_text}
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
        result = _call_ai(prompt)
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

    if incident.ai_confidence >= 0.65:
        _transition(incident, 'VERIFIED', 'AI',
                    f'Auto-verified. Confidence: {incident.ai_confidence:.2f}')
        incident.save()
        _post_verification_actions(incident)
    elif incident.ai_confidence >= 0.4:
        _transition(incident, 'VERIFYING', 'AI', 'Awaiting community vouches')
        incident.save()
        _notify_verifying(incident)
    else:
        _transition(incident, 'REJECTED', 'AI', 'Insufficient confidence')
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

    try:
        from apps.responders.tasks import notify_nearest_responders
        if incident.severity in ['CRITICAL', 'HIGH', 'MEDIUM']:
            notify_nearest_responders.delay(str(incident.id))
    except Exception:
        pass

    try:
        from apps.organisations.tasks import notify_nearest_organisations
        notify_nearest_organisations.delay(str(incident.id))
    except Exception:
        pass

    try:
        from apps.subscriptions.tasks import notify_location_subscribers
        notify_location_subscribers.delay(str(incident.id))
    except Exception:
        pass

    # v5: Commute Shield -- runs for all road/infrastructure/flood incidents
    try:
        if incident.is_infrastructure or incident.incident_type in ['HAZARD', 'RTA', 'FLOOD']:
            from apps.subscriptions.tasks import notify_commute_shield
            notify_commute_shield.delay(str(incident.id))
    except Exception:
        pass


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
