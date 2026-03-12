import hashlib
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from apps.incidents.models import Incident
from apps.incidents.tasks import verify_incident_ai


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

    verify_incident_ai.delay(str(incident.id))

    return Response(
        {'id': str(incident.id), 'tracking_url': f'/track/{incident.id}'},
        status=status.HTTP_201_CREATED
    )
