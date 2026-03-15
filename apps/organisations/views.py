import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Organisation
from .serializers import OrganisationSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_organisation(request):
    """Self-registration. Creates PENDING organisation."""
    serializer = OrganisationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    org = serializer.save(status='PENDING')
    return Response({'id': str(org.id), 'status': 'PENDING'}, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def organisation_respond(request, pk):
    """Confirm or decline capacity for an incident."""
    try:
        org = Organisation.objects.get(pk=pk)
    except Organisation.DoesNotExist:
        return Response({'error': 'Organisation not found'}, status=404)

    can_receive = request.data.get('can_receive')
    if can_receive is None:
        return Response({'error': 'can_receive is required'}, status=400)

    if can_receive:
        org.total_responses += 1
        org.save(update_fields=['total_responses'])
        try:
            from apps.incidents.models import Incident
            from apps.whatsapp.tasks import send_whatsapp_text
            from apps.whatsapp import templates as tmpl
            incident = Incident.objects.filter(
                status__in=['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED']
            ).order_by('-created_at').first()
            if incident and org.contact_whatsapp:
                send_whatsapp_text.delay(
                    org.contact_whatsapp,
                    tmpl.org_accept_ack(org, incident)
                )
        except Exception as exc:
            logger.warning("organisation_respond send error: %s", exc)

    return Response({'can_receive': can_receive})


@api_view(['GET'])
@permission_classes([AllowAny])
def organisations_map(request):
    """All VERIFIED organisations for map display."""
    orgs = Organisation.objects.filter(status='VERIFIED')
    serializer = OrganisationSerializer(orgs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def organisation_detail(request, pk):
    """Public org profile."""
    try:
        org = Organisation.objects.get(pk=pk)
    except Organisation.DoesNotExist:
        return Response({'error': 'Organisation not found'}, status=404)
    serializer = OrganisationSerializer(org)
    return Response(serializer.data)
