import hashlib
import logging

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
    body = request.POST.get('Body', '').strip()

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

    # Route in background
    try:
        from apps.whatsapp.handlers import route_inbound
        route_inbound(from_number, body, media_urls, location)
    except Exception as exc:
        logger.exception("route_inbound error: %s", exc)

    return HttpResponse('', status=200)


@api_view(['POST'])
@permission_classes([AllowAny])
def web_ingest(request):
    description = request.data.get('description', '').strip()
    if not description:
        return Response({'error': 'description is required'}, status=status.HTTP_400_BAD_REQUEST)

    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
    reporter_hash = hashlib.sha256(ip.encode()).hexdigest()

    incident = Incident.objects.create(
        source='WEB',
        reporter_hash=reporter_hash,
        description=description,
        location_lat=request.data.get('location_lat'),
        location_lng=request.data.get('location_lng'),
        address_text=request.data.get('address_text', ''),
        incident_type=request.data.get('incident_type', ''),
        media_urls=request.data.get('media_urls', []),
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
