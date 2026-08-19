import hashlib
import logging

from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from apps.incidents.models import Incident
from apps.incidents.tasks import verify_incident_ai
from utils.ratelimit import hit_rate_limit, masked

# Bound the stored/AI-processed report text. Unbounded input inflates the
# AI prompt (cost + injection surface) and the database row.
MAX_DESCRIPTION_CHARS = 2000

logger = logging.getLogger(__name__)


@csrf_exempt
@require_POST
def whatsapp_ingest(request):
    """
    Twilio webhook. Validates X-Twilio-Signature.
    Responds 200 immediately. Routes message via handlers.
    """
    # Validate Twilio signature
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        url = request.build_absolute_uri()
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        signature = request.META.get('HTTP_X_TWILIO_SIGNATURE', '')
        params = dict(request.POST)
        # request.POST is a QueryDict — convert to plain dict of single values
        flat_params = {k: v[0] if isinstance(v, list) and len(v) == 1 else v
                       for k, v in params.items()}
        if not validator.validate(url, flat_params, signature):
            logger.warning("Invalid Twilio signature from %s", request.META.get('REMOTE_ADDR'))
            return HttpResponse('Forbidden', status=403)
    except Exception as exc:
        logger.error("Twilio signature validation error: %s", exc)
        return HttpResponse('Forbidden', status=403)

    # Extract fields
    from_raw = request.POST.get('From', '')
    from_number = from_raw.replace('whatsapp:', '')
    body = request.POST.get('Body', '').strip()[:MAX_DESCRIPTION_CHARS]

    # Rate limit: 10 messages/60s per sender, keyed on the NORMALISED phone
    # hash (BRD §7) so reformatting the number cannot reset the quota.
    if hit_rate_limit(from_number, rate=10, window=60, scope='wa'):
        logger.warning("whatsapp_ingest: rate limit exceeded for %s", masked(from_number))
        return HttpResponse('', status=200)  # 200 so Twilio does not retry

    num_media = int(request.POST.get('NumMedia', 0))
    media_urls = [
        request.POST.get(f'MediaUrl{i}', '')
        for i in range(num_media)
        if request.POST.get(f'MediaUrl{i}')
    ]

    location = None
    lat = request.POST.get('Latitude')
    lng = request.POST.get('Longitude')
    if lat and lng:
        try:
            location = {'latitude': float(lat), 'longitude': float(lng)}
        except ValueError:
            pass

    # Route in background via Celery — avoids Twilio 15s timeout
    try:
        from apps.whatsapp.tasks import handle_whatsapp_message
        handle_whatsapp_message.delay(from_number, body, media_urls, location)
    except Exception as exc:
        logger.exception("Failed to queue whatsapp task: %s", exc)

    return HttpResponse('', status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def web_ingest(request):
    """Public web report intake.

    SECURITY: this endpoint was previously unauthenticated AND unthrottled,
    and passed `media_urls` straight from the request body into the model —
    letting anyone attach arbitrary URLs to a public incident page and spam
    incident creation (each of which triggers a paid AI call).
    """
    description = str(request.data.get('description', '') or '').strip()
    if not description:
        return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)
    description = description[:MAX_DESCRIPTION_CHARS]

    # NOTE: behind Railway's proxy X-Forwarded-For is the only per-client
    # signal available, and a determined attacker can spoof it. This throttle
    # is therefore best-effort abuse reduction, not an authorisation control.
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() \
        or request.META.get('REMOTE_ADDR', 'unknown')
    if hit_rate_limit(client_ip, rate=5, window=60, scope='web'):
        logger.warning("web_ingest: rate limit exceeded")
        return Response({'error': 'Too many reports. Please wait a moment.'},
                        status=status.HTTP_429_TOO_MANY_REQUESTS)

    def _coord(value):
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        return f if -180 <= f <= 180 else None

    incident = Incident.objects.create(
        source='WEB',
        reporter_hash=hashlib.sha256(client_ip.encode()).hexdigest(),
        description=description,
        location_lat=_coord(request.data.get('location_lat')),
        location_lng=_coord(request.data.get('location_lng')),
        address_text=str(request.data.get('address_text', '') or '')[:500],
        # incident_type/media_urls are NOT accepted from the client:
        # classification is the AI's job and media URLs are staff-managed.
        status='DETECTED',
    )

    try:
        verify_incident_ai.delay(str(incident.id))
    except Exception as exc:
        logger.warning("Could not queue verify task for %s: %s", incident.id, exc)

    return Response(
        {'id': str(incident.id), 'tracking_url': f'/track/{incident.id}'},
        status=status.HTTP_201_CREATED
    )
