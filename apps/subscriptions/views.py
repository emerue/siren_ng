import hashlib
from datetime import timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import LocationSubscription, LGASubscription, SubscriptionAlert, SafetyScoreLog
from .serializers import LocationSubscriptionSerializer, LGASubscriptionSerializer
# LocationSubscriptionSerializer kept for commute_create response


AVAILABLE_LGAS = sorted([
    'Agege', 'Ajeromi-Ifelodun', 'Alimosho', 'Amuwo-Odofin', 'Apapa',
    'Badagry', 'Epe', 'Eti-Osa', 'Ibeju-Lekki', 'Ifako-Ijaiye',
    'Ikorodu', 'Ikeja', 'Kosofe', 'Lagos Island', 'Lagos Mainland',
    'Mushin', 'Ojo', 'Oshodi-Isolo', 'Shomolu', 'Somolu', 'Surulere',
])


class LGASubscriptionViewSet(viewsets.ModelViewSet):
    """API endpoints for LGA-based Guardian Mode subscriptions."""
    serializer_class = LGASubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LGASubscription.objects.filter(user=self.request.user).order_by('-created_at')

    def create(self, request, *args, **kwargs):
        lga = request.data.get('lga', '').strip()
        if not lga:
            return Response({'error': 'lga is required'}, status=status.HTTP_400_BAD_REQUEST)

        existing = LGASubscription.objects.filter(user=request.user, lga=lga).first()
        if existing:
            if existing.is_active:
                return Response(
                    {'detail': f'Already subscribed to {lga}'},
                    status=status.HTTP_200_OK,
                )
            existing.is_active = True
            existing.save(update_fields=['is_active', 'updated_at'])
            return Response(self.get_serializer(existing).data, status=status.HTTP_200_OK)

        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
        return Response({'detail': f'Unsubscribed from {instance.lga}'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def available_lgas(self, request):
        """GET /api/subscriptions/lga/available_lgas/ — list all Lagos LGAs."""
        return Response({'lgas': AVAILABLE_LGAS})




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
