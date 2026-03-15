import hashlib
from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import LocationSubscription, SubscriptionAlert, SafetyScoreLog
from .serializers import LocationSubscriptionSerializer


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def subscription_list_create(request):
    if request.method == 'GET':
        phone_hash = request.query_params.get('phone_hash', '')
        if not phone_hash:
            return Response({'error': 'phone_hash query param is required'}, status=400)
        subs = LocationSubscription.objects.filter(phone_hash=phone_hash)
        serializer = LocationSubscriptionSerializer(subs, many=True)
        return Response(serializer.data)

    # POST -- create subscription
    data = request.data
    whatsapp_number = data.get('whatsapp_number', '').strip()
    if not whatsapp_number:
        return Response({'error': 'whatsapp_number is required'}, status=400)

    phone_hash = hashlib.sha256(whatsapp_number.encode()).hexdigest()

    serializer = LocationSubscriptionSerializer(data={
        'whatsapp_number': whatsapp_number,
        'label': data.get('label', 'My location'),
        'location_type': data.get('location_type', 'HOME'),
        'location_lat': data.get('location_lat'),
        'location_lng': data.get('location_lng'),
        'alert_radius_km': data.get('alert_radius_km', 1.0),
        'incident_types': data.get('incident_types', []),
    })
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    sub = serializer.save(phone_hash=phone_hash)
    return Response(LocationSubscriptionSerializer(sub).data, status=201)


@api_view(['PATCH', 'DELETE'])
@permission_classes([AllowAny])
def subscription_detail(request, pk):
    try:
        sub = LocationSubscription.objects.get(pk=pk)
    except LocationSubscription.DoesNotExist:
        return Response({'error': 'Subscription not found'}, status=404)

    if request.method == 'DELETE':
        sub.delete()
        return Response(status=204)

    # PATCH
    allowed = ['label', 'alert_radius_km', 'is_active', 'incident_types', 'address_text']
    for field in allowed:
        if field in request.data:
            setattr(sub, field, request.data[field])
    sub.save()
    return Response(LocationSubscriptionSerializer(sub).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def commute_create(request):
    """
    POST /api/subscriptions/commute/
    Creates a COMMUTE subscription with home + office coordinates.
    """
    data = request.data
    whatsapp_number = data.get('whatsapp_number', '').strip()
    if not whatsapp_number:
        return Response({'error': 'whatsapp_number is required'}, status=400)

    required = ['location_lat', 'location_lng', 'office_lat', 'office_lng']
    for field in required:
        if not data.get(field):
            return Response({'error': f'{field} is required'}, status=400)

    phone_hash = hashlib.sha256(whatsapp_number.encode()).hexdigest()

    sub = LocationSubscription.objects.create(
        phone_hash=phone_hash,
        whatsapp_number=whatsapp_number,
        label=data.get('label', 'My commute'),
        location_type='HOME',
        location_lat=float(data['location_lat']),
        location_lng=float(data['location_lng']),
        office_lat=float(data['office_lat']),
        office_lng=float(data['office_lng']),
        subscription_type='COMMUTE',
        commute_buffer_km=float(data.get('commute_buffer_km', 1.5)),
        peak_only=True,
    )
    return Response(LocationSubscriptionSerializer(sub).data, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def my_impact(request):
    """
    GET /api/subscriptions/my-impact/?phone_hash=...
    Returns impact data for the /my-impact page. No auth required.
    """
    phone_hash = request.query_params.get('phone_hash', '')
    if not phone_hash:
        return Response({'error': 'phone_hash is required'}, status=400)

    subs = LocationSubscription.objects.filter(phone_hash=phone_hash)
    if not subs.exists():
        return Response({'error': 'No subscriptions found for this phone_hash'}, status=404)

    from apps.incidents.models import Incident
    from apps.resources.models import Donation

    cutoff_30 = timezone.now() - timedelta(days=30)

    # Build per-subscription data
    sub_data = []
    total_alerts = 0
    incidents_near_ids = set()
    incidents_resolved_near_ids = set()

    for sub in subs:
        alerts = SubscriptionAlert.objects.filter(subscription=sub)
        total_alerts += alerts.count()
        alert_incident_ids = alerts.values_list('incident_id', flat=True)
        incidents_near_ids.update(str(i) for i in alert_incident_ids)
        resolved_ids = Incident.objects.filter(
            id__in=alert_incident_ids, status='RESOLVED'
        ).values_list('id', flat=True)
        incidents_resolved_near_ids.update(str(i) for i in resolved_ids)

        score_logs = SafetyScoreLog.objects.filter(
            subscription=sub
        ).order_by('-created_at')[:30]

        sub_data.append({
            'id': str(sub.id),
            'label': sub.label,
            'subscription_type': sub.subscription_type,
            'safety_score': sub.safety_score,
            'alert_radius_km': sub.alert_radius_km,
            'is_active': sub.is_active,
            'score_logs': [
                {
                    'score': log.score,
                    'reason': log.reason,
                    'created_at': log.created_at.isoformat(),
                }
                for log in score_logs
            ],
        })

    # Total donations on incidents the user was alerted to
    total_donations = 0.0
    if incidents_near_ids:
        from django.db.models import Sum
        result = Donation.objects.filter(
            incident_id__in=incidents_near_ids,
            status='SUCCESS',
        ).aggregate(total=Sum('amount_kobo'))
        total_kobo = result.get('total') or 0
        total_donations = total_kobo / 100

    # Responders triggered near user's locations
    from apps.responders.models import ResponderDispatch
    responders_triggered = ResponderDispatch.objects.filter(
        incident_id__in=incidents_near_ids,
        accepted=True,
    ).count()

    return Response({
        'subscriptions': sub_data,
        'total_alerts_received': total_alerts,
        'incidents_near_count': len(incidents_near_ids),
        'incidents_resolved_near': len(incidents_resolved_near_ids),
        'total_donations_on_alerted_incidents': total_donations,
        'responders_triggered_count': responders_triggered,
    })
