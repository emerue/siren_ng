import json
import re
from celery import shared_task
from django.conf import settings
import anthropic


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def verify_incident_ai(self, incident_id: str):
    """
    Calls Claude to classify and verify an incident.
    Updates status. Triggers all downstream notifications if VERIFIED.
    """
    from apps.incidents.models import Incident

    incident = Incident.objects.get(id=incident_id)

    prompt = f"""You are an emergency verification system for Lagos, Nigeria.
Analyse this report and respond ONLY with valid JSON. No markdown. No explanation.

Report: {incident.description}
Location text: {incident.address_text}

Return this exact JSON:
{{
  "eligible": true or false,
  "rejection_reason": "why rejected, or null if eligible",
  "incident_type": "FIRE|FLOOD|COLLAPSE|RTA|EXPLOSION|DROWNING|HAZARD or null",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "ai_confidence": 0.0 to 1.0,
  "fraud_score": 0.0 to 1.0,
  "suggested_skills": ["list of skill codes"],
  "reasoning": "one sentence"
}}

Only these types qualify: FIRE FLOOD COLLAPSE RTA EXPLOSION DROWNING HAZARD
fraud_score above 0.7 means the report looks fake."""

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1024,
            messages=[{'role': 'user', 'content': prompt}]
        )
        text = message.content[0].text.strip()
        text = re.sub(r'```json|```', '', text).strip()  # Strip code fences
        result = json.loads(text)
    except Exception as exc:
        raise self.retry(exc=exc)

    incident.ai_raw_response = result
    incident.ai_confidence   = result.get('ai_confidence', 0.0)
    incident.fraud_score     = result.get('fraud_score', 0.0)

    if not result.get('eligible') or incident.fraud_score > 0.7:
        _transition(incident, 'REJECTED', 'AI', result.get('rejection_reason', ''))
        incident.save()
        _notify_rejected(incident, result.get('rejection_reason', ''))
        return

    incident.incident_type = result.get('incident_type', '')
    incident.severity      = result.get('severity', 'MEDIUM')
    incident.set_vouch_threshold()

    if incident.ai_confidence >= 0.75:
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
        pass  # Redis/channel layer unavailable — do not block status save


def _post_verification_actions(incident):
    try:
        from apps.whatsapp.tasks import notify_reporter_verified, post_community_announcement
        notify_reporter_verified.delay(str(incident.id))
        post_community_announcement.delay(str(incident.id))
    except Exception:
        pass

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
