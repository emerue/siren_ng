import hashlib
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Incident, VouchRecord
from .serializers import IncidentSerializer, IncidentDetailSerializer



class IncidentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class IncidentListView(generics.ListAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [AllowAny]
    pagination_class = IncidentPagination

    def get_queryset(self):
        qs = Incident.objects.filter(
            status__in=['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED']
        )
        if zone := self.request.query_params.get('zone_name'):
            qs = qs.filter(zone_name=zone)
        if s := self.request.query_params.get('status'):
            qs = qs.filter(status=s)
        if t := self.request.query_params.get('incident_type'):
            qs = qs.filter(incident_type=t)
        if sev := self.request.query_params.get('severity'):
            qs = qs.filter(severity=sev)
        return qs


@api_view(['GET'])
@permission_classes([AllowAny])
def active_incidents(request):
    qs = Incident.objects.filter(status__in=['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED'])
    serializer = IncidentSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def incident_detail(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    serializer = IncidentDetailSerializer(incident)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def incident_track(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    latest_log = incident.response_logs.last()
    return Response({
        'id': str(incident.id),
        'status': incident.status,
        'incident_type': incident.incident_type,
        'severity': incident.severity,
        'address_text': incident.address_text,
        'zone_name': incident.zone_name,
        'vouch_count': incident.vouch_count,
        'total_donations_naira': incident.total_donations_naira,
        'created_at': incident.created_at,
        'updated_at': incident.updated_at,
        'latest_log': {
            'to_status': latest_log.to_status,
            'note': latest_log.note,
            'actor': latest_log.actor,
            'created_at': latest_log.created_at,
        } if latest_log else None,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def incident_vouch(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
    ua = request.META.get('HTTP_USER_AGENT', '')
    session_hash = hashlib.sha256(f"{ip}{ua}{pk}".encode()).hexdigest()

    if VouchRecord.objects.filter(incident=incident, session_hash=session_hash).exists():
        return Response({'error': 'Already vouched'}, status=status.HTTP_400_BAD_REQUEST)

    VouchRecord.objects.create(
        incident=incident,
        session_hash=session_hash,
        voucher_lat=request.data.get('lat'),
        voucher_lng=request.data.get('lng'),
    )
    incident.vouch_count += 1
    incident.save(update_fields=['vouch_count'])
    return Response({'vouch_count': incident.vouch_count})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def incident_dispatch(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    from apps.incidents.tasks import _transition
    _transition(incident, 'AGENCY_NOTIFIED', f'agency:{request.user}')
    incident.save()
    return Response({'status': incident.status})


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def incident_resolve(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    from apps.incidents.tasks import _transition
    _transition(incident, 'RESOLVED', f'agency:{request.user}')
    incident.resolved_at = timezone.now()
    incident.save()
    return Response({'status': incident.status})
