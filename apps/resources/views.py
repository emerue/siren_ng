import hashlib
import hmac
import json
import logging
import uuid as _uuid

import requests
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import ResourceItem, ResourceClaim, Donation
from .serializers import (
    ResourceItemSerializer, ResourceClaimSerializer,
    DonationSerializer, DonationSummarySerializer,
)

logger = logging.getLogger(__name__)


# ── Resource Board ─────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def resource_list_create(request):
    if request.method == 'GET':
        incident_id = request.query_params.get('incident')
        if not incident_id:
            return Response({'error': 'incident query param is required'}, status=400)
        items = ResourceItem.objects.filter(incident_id=incident_id)
        serializer = ResourceItemSerializer(items, many=True)
        return Response(serializer.data)

    # POST — suggest a new resource
    data = request.data
    incident_id = data.get('incident')
    if not incident_id:
        return Response({'error': 'incident is required'}, status=400)

    session_hash = data.get('session_hash', '')
    if not session_hash:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'anon'))
        session_hash = hashlib.sha256(ip.encode()).hexdigest()

    item = ResourceItem.objects.create(
        incident_id=incident_id,
        category=data.get('category', 'OTHER'),
        label=data.get('label', ''),
        suggested_by_hash=session_hash,
        suggested_by_name=data.get('suggested_by_name', ''),
        suggested_via=data.get('suggested_via', 'WEB'),
    )
    serializer = ResourceItemSerializer(item)
    return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def resource_claim(request, pk):
    try:
        item = ResourceItem.objects.get(pk=pk)
    except ResourceItem.DoesNotExist:
        return Response({'error': 'Resource not found'}, status=404)

    data = request.data
    session_hash = data.get('session_hash', '')
    if not session_hash:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'anon'))
        session_hash = hashlib.sha256(ip.encode()).hexdigest()

    try:
        ResourceClaim.objects.create(
            resource=item,
            claimer_hash=session_hash,
            claimer_name=data.get('claimer_name', ''),
            claimer_phone=data.get('claimer_phone', ''),
        )
        if item.status == 'NEEDED':
            item.status = 'CLAIMED'
            item.save(update_fields=['status'])
    except IntegrityError:
        return Response({'message': 'You have already claimed this item'})

    serializer = ResourceItemSerializer(item)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([AllowAny])
def resource_confirm(request, pk):
    try:
        item = ResourceItem.objects.get(pk=pk)
    except ResourceItem.DoesNotExist:
        return Response({'error': 'Resource not found'}, status=404)

    confirmer_hash = request.data.get('confirmer_hash', '')
    item.status = 'ARRIVED'
    item.confirmed_by_hash = confirmer_hash
    item.confirmed_at = timezone.now()
    item.save(update_fields=['status', 'confirmed_by_hash', 'confirmed_at'])

    # Broadcast WebSocket update
    try:
        from apps.incidents.consumers import broadcast_update
        broadcast_update(item.incident)
    except Exception:
        pass

    serializer = ResourceItemSerializer(item)
    return Response(serializer.data)


# ── Donations ─────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def donate_initiate(request):
    data = request.data
    incident_id = data.get('incident_id')
    amount_naira = data.get('amount_naira')
    fund_choice = data.get('fund_choice', 'VICTIM')
    donor_email = data.get('donor_email', '')

    if not incident_id or not amount_naira or not donor_email:
        return Response({'error': 'incident_id, amount_naira, and donor_email are required'}, status=400)

    try:
        amount_naira = float(amount_naira)
    except (ValueError, TypeError):
        return Response({'error': 'amount_naira must be a number'}, status=400)

    if amount_naira < 500:
        return Response({'error': 'Minimum donation is ₦500'}, status=400)

    amount_kobo = int(amount_naira * 100)

    # Determine subaccount
    if fund_choice == 'PLATFORM':
        subaccount = settings.SIREN_PAYSTACK_SUBACCOUNT
    elif fund_choice == 'VICTIM':
        subaccount = settings.SIREN_PAYSTACK_SUBACCOUNT
    else:  # RESPONDER
        subaccount = settings.SIREN_PAYSTACK_SUBACCOUNT

    reference = str(_uuid.uuid4())

    donation = Donation.objects.create(
        incident_id=incident_id,
        donor_name=data.get('donor_name', ''),
        donor_email=donor_email,
        donor_phone=data.get('donor_phone', ''),
        amount_kobo=amount_kobo,
        fund_choice=fund_choice,
        status='PENDING',
        paystack_reference=reference,
        recipient_subaccount=subaccount,
    )

    # Call Paystack initialize
    try:
        resp = requests.post(
            'https://api.paystack.co/transaction/initialize',
            headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
            json={
                'email': donor_email,
                'amount': amount_kobo,
                'reference': reference,
                'subaccount': subaccount,
                'transaction_charge': int(amount_kobo * 0.10),  # Siren 10% cut
                'callback_url': f'{getattr(settings, "SITE_URL", "https://siren.ng")}/donate/success?ref={reference}',
            },
            timeout=15,
        )
        resp.raise_for_status()
        paystack_data = resp.json()
        payment_url = paystack_data['data']['authorization_url']
    except Exception as exc:
        logger.error("Paystack initialize error: %s", exc)
        donation.delete()
        return Response({'error': 'Payment gateway error. Please try again.'}, status=502)

    return Response({'payment_url': payment_url, 'reference': reference}, status=201)


@csrf_exempt
def donate_verify(request):
    """Paystack webhook callback. Validates signature, updates donation."""
    if request.method != 'POST':
        from django.http import HttpResponse
        return HttpResponse('Method not allowed', status=405)

    # Validate Paystack signature
    sig = request.META.get('HTTP_X_PAYSTACK_SIGNATURE', '')
    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        request.body,
        digestmod='sha512',
    ).hexdigest()
    if not hmac.compare_digest(sig, expected):
        logger.warning("Invalid Paystack signature")
        from django.http import HttpResponse
        return HttpResponse('Forbidden', status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        from django.http import HttpResponse
        return HttpResponse('Bad request', status=400)

    event = payload.get('event')
    if event != 'charge.success':
        from django.http import HttpResponse
        return HttpResponse('OK', status=200)

    reference = payload.get('data', {}).get('reference', '')

    try:
        donation = Donation.objects.select_related('incident').get(
            paystack_reference=reference
        )
    except Donation.DoesNotExist:
        from django.http import HttpResponse
        return HttpResponse('OK', status=200)

    if donation.status == 'SUCCESS':
        from django.http import HttpResponse
        return HttpResponse('OK', status=200)  # Idempotent

    donation.status = 'SUCCESS'
    donation.confirmed_at = timezone.now()
    donation.paystack_response = payload
    donation.save(update_fields=['status', 'confirmed_at', 'paystack_response'])

    # Update incident totals
    incident = donation.incident
    incident.total_donations_kobo += donation.amount_kobo
    incident.donation_count += 1
    incident.save(update_fields=['total_donations_kobo', 'donation_count'])

    # Responder payout split
    if donation.fund_choice == 'RESPONDER':
        _trigger_responder_payout(incident, donation)

    # Broadcast WebSocket update
    try:
        from apps.incidents.consumers import broadcast_update
        broadcast_update(incident)
    except Exception:
        pass

    # Thank-you WhatsApp
    if donation.donor_phone:
        try:
            from apps.whatsapp.tasks import send_whatsapp_text
            from apps.whatsapp import templates as tmpl
            send_whatsapp_text.delay(
                donation.donor_phone,
                tmpl.donation_thank_you(
                    donation.donor_name,
                    donation.amount_naira,
                    donation.fund_choice,
                    incident,
                )
            )
        except Exception as exc:
            logger.warning("donate_verify thank-you send error: %s", exc)

    from django.http import HttpResponse
    return HttpResponse('OK', status=200)


def _trigger_responder_payout(incident, donation):
    """Split RESPONDER donation among on-scene responders via Paystack Transfer."""
    try:
        from apps.responders.models import ResponderDispatch
        dispatches = ResponderDispatch.objects.filter(
            incident=incident,
            on_scene_at__isnull=False,
        ).select_related('responder')

        subaccounts = [
            d.responder.paystack_subaccount
            for d in dispatches
            if d.responder.paystack_subaccount
        ]
        if not subaccounts:
            return  # Hold in Siren account

        share_kobo = int(donation.amount_kobo * 0.9 / len(subaccounts))
        for subaccount in subaccounts:
            try:
                requests.post(
                    'https://api.paystack.co/transfer',
                    headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
                    json={
                        'source': 'balance',
                        'amount': share_kobo,
                        'recipient': subaccount,
                        'reason': f'Responder appreciation — incident {incident.id}',
                    },
                    timeout=10,
                )
            except Exception as exc:
                logger.error("Responder payout error for %s: %s", subaccount, exc)
    except Exception as exc:
        logger.error("_trigger_responder_payout error: %s", exc)


@api_view(['GET'])
@permission_classes([AllowAny])
def donate_summary(request):
    """Public donation summary for an incident."""
    incident_id = request.query_params.get('incident')
    if not incident_id:
        return Response({'error': 'incident query param is required'}, status=400)

    from django.db.models import Sum, Count
    donations = Donation.objects.filter(incident_id=incident_id, status='SUCCESS')
    agg = donations.aggregate(total=Sum('amount_kobo'), count=Count('id'))
    total_kobo = agg['total'] or 0
    count = agg['count'] or 0

    fund_rows = (
        donations.values('fund_choice')
        .annotate(total=Sum('amount_kobo'))
    )
    fund_breakdown = {row['fund_choice']: row['total'] / 100 for row in fund_rows}

    data = {
        'total_naira': total_kobo / 100,
        'donation_count': count,
        'fund_breakdown': fund_breakdown,
    }
    serializer = DonationSummarySerializer(data)
    return Response(serializer.data)
