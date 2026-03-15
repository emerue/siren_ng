import hashlib
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import Responder, ResponderDispatch
from .serializers import ResponderSerializer, ResponderDispatchSerializer

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_responder(request):
    """Self-registration. Creates PENDING responder."""
    data = request.data

    phone = data.get('whatsapp_number', '').strip()
    if not phone:
        return Response({'error': 'whatsapp_number is required'}, status=400)

    phone_hash = hashlib.sha256(phone.encode()).hexdigest()

    if Responder.objects.filter(phone_hash=phone_hash).exists():
        return Response({'error': 'This number is already registered.'}, status=400)

    serializer = ResponderSerializer(data={
        'name': data.get('name', ''),
        'skill_category': data.get('skill_category', ''),
        'home_lat': data.get('home_lat'),
        'home_lng': data.get('home_lng'),
        'response_radius_km': data.get('response_radius_km', 2.0),
        'responds_to': data.get('responds_to', []),
        'zone_name': data.get('zone_name', ''),
        'licence_number': data.get('licence_number', ''),
    })
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    responder = serializer.save(
        phone_hash=phone_hash,
        whatsapp_number=phone,
        status='PENDING',
    )
    return Response({'id': str(responder.id), 'status': 'PENDING'}, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def toggle_availability(request):
    """Toggle responder availability by phone_hash."""
    phone_hash = request.data.get('phone_hash', '').strip()
    is_available = request.data.get('is_available')

    if not phone_hash or is_available is None:
        return Response({'error': 'phone_hash and is_available are required'}, status=400)

    try:
        responder = Responder.objects.get(phone_hash=phone_hash)
    except Responder.DoesNotExist:
        return Response({'error': 'Responder not found'}, status=404)

    responder.is_available = bool(is_available)
    responder.save(update_fields=['is_available'])
    return Response({'is_available': responder.is_available})


@api_view(['POST'])
@permission_classes([AllowAny])
def dispatch_accept(request, pk):
    try:
        dispatch = ResponderDispatch.objects.select_related('responder', 'incident').get(pk=pk)
    except ResponderDispatch.DoesNotExist:
        return Response({'error': 'Dispatch not found'}, status=404)

    dispatch.accepted = True
    dispatch.save(update_fields=['accepted'])

    incident = dispatch.incident
    if incident.status not in ('RESPONDING', 'AGENCY_NOTIFIED', 'RESOLVED'):
        incident.status = 'RESPONDING'
        incident.save(update_fields=['status'])

    # Send directions via WhatsApp
    try:
        from apps.whatsapp.tasks import send_whatsapp_text
        from apps.whatsapp import templates as tmpl
        send_whatsapp_text.delay(
            dispatch.responder.whatsapp_number,
            tmpl.responder_directions(dispatch.responder, incident)
        )
    except Exception as exc:
        logger.warning("dispatch_accept send error: %s", exc)

    return Response({'accepted': True})


@api_view(['POST'])
@permission_classes([AllowAny])
def dispatch_decline(request, pk):
    try:
        dispatch = ResponderDispatch.objects.select_related('responder', 'incident').get(pk=pk)
    except ResponderDispatch.DoesNotExist:
        return Response({'error': 'Dispatch not found'}, status=404)

    dispatch.accepted = False
    dispatch.save(update_fields=['accepted'])

    # Notify next nearest, excluding this responder
    try:
        from apps.responders.tasks import notify_nearest_responders
        notify_nearest_responders.delay(
            str(dispatch.incident.id),
            exclude_ids=[str(dispatch.responder.id)]
        )
    except Exception as exc:
        logger.warning("dispatch_decline re-notify error: %s", exc)

    return Response({'accepted': False})


@api_view(['POST'])
@permission_classes([AllowAny])
def dispatch_onscene(request, pk):
    try:
        dispatch = ResponderDispatch.objects.select_related('responder', 'incident').get(pk=pk)
    except ResponderDispatch.DoesNotExist:
        return Response({'error': 'Dispatch not found'}, status=404)

    dispatch.on_scene_at = timezone.now()
    dispatch.save(update_fields=['on_scene_at'])

    try:
        from apps.whatsapp.tasks import send_whatsapp_text
        from apps.whatsapp import templates as tmpl
        send_whatsapp_text.delay(
            dispatch.responder.whatsapp_number,
            tmpl.responder_onscene_ack(dispatch.responder, dispatch.incident)
        )
    except Exception as exc:
        logger.warning("dispatch_onscene send error: %s", exc)

    return Response({'on_scene_at': dispatch.on_scene_at})


@api_view(['POST'])
@permission_classes([AllowAny])
def dispatch_complete(request, pk):
    try:
        dispatch = ResponderDispatch.objects.select_related('responder', 'incident').get(pk=pk)
    except ResponderDispatch.DoesNotExist:
        return Response({'error': 'Dispatch not found'}, status=404)

    dispatch.completed_at = timezone.now()
    dispatch.save(update_fields=['completed_at'])

    responder = dispatch.responder
    responder.total_responses += 1
    responder.save(update_fields=['total_responses'])

    try:
        from apps.whatsapp.tasks import send_whatsapp_text
        from apps.whatsapp import templates as tmpl
        send_whatsapp_text.delay(
            responder.whatsapp_number,
            tmpl.responder_done_ack(dispatch.incident)
        )
    except Exception as exc:
        logger.warning("dispatch_complete send error: %s", exc)

    return Response({'completed_at': dispatch.completed_at})
