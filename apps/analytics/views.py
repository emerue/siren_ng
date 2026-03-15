from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncDay

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def _date_range(request):
    range_param = request.query_params.get('range', '7d')
    days = {'7d': 7, '30d': 30, '90d': 90}.get(range_param, 7)
    since = timezone.now() - timedelta(days=days)
    return since


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_summary(request):
    from apps.incidents.models import Incident
    from apps.responders.models import Responder
    from apps.resources.models import Donation

    since = _date_range(request)
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    active = Incident.objects.filter(
        status__in=['VERIFIED', 'RESPONDING', 'AGENCY_NOTIFIED']
    ).count()
    today_total = Incident.objects.filter(created_at__gte=today_start).count()
    responders_available = Responder.objects.filter(
        status='VERIFIED', is_available=True
    ).count()
    donated_today_kobo = (
        Donation.objects
        .filter(status='SUCCESS', confirmed_at__gte=today_start)
        .aggregate(total=Sum('amount_kobo'))['total'] or 0
    )

    return Response({
        'active_incidents': active,
        'today_total': today_total,
        'responders_available': responders_available,
        'total_donated_today_naira': donated_today_kobo / 100,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_zones(request):
    from apps.incidents.models import Incident

    since = _date_range(request)
    rows = (
        Incident.objects
        .filter(created_at__gte=since)
        .values('zone_name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    return Response(list(rows))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_trends(request):
    from apps.incidents.models import Incident

    since = _date_range(request)
    rows = (
        Incident.objects
        .filter(created_at__gte=since)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    return Response([
        {'day': r['day'].strftime('%Y-%m-%d'), 'count': r['count']}
        for r in rows
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_donations(request):
    from apps.resources.models import Donation

    since = _date_range(request)
    total_kobo = (
        Donation.objects
        .filter(status='SUCCESS', confirmed_at__gte=since)
        .aggregate(total=Sum('amount_kobo'))['total'] or 0
    )
    per_fund = (
        Donation.objects
        .filter(status='SUCCESS', confirmed_at__gte=since)
        .values('fund_choice')
        .annotate(total=Sum('amount_kobo'))
    )
    return Response({
        'total_naira': total_kobo / 100,
        'per_fund': [
            {'fund': r['fund_choice'], 'naira': r['total'] / 100}
            for r in per_fund
        ],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_subscribers(request):
    from apps.subscriptions.models import LocationSubscription, SubscriptionAlert

    active_subs = LocationSubscription.objects.filter(is_active=True).count()
    total_alerts = SubscriptionAlert.objects.count()

    since = _date_range(request)
    alerts_in_range = SubscriptionAlert.objects.filter(sent_at__gte=since).count()

    return Response({
        'active_subscriptions': active_subs,
        'total_alerts_sent': total_alerts,
        'alerts_in_range': alerts_in_range,
    })
