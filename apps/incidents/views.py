import hashlib
import logging
from datetime import datetime, timedelta, timezone as dt_timezone

from django.db.models import Count
from django.db.models.functions import ExtractYear
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Incident, VouchRecord, IncidentMedia
from .serializers import IncidentSerializer, IncidentDetailSerializer, IncidentMediaSerializer

logger = logging.getLogger(__name__)

MAX_MEDIA_PER_INCIDENT = 5


def _session_hash(request, incident_pk):
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "unknown"))
    ua = request.META.get("HTTP_USER_AGENT", "")
    return hashlib.sha256(f"{ip}{ua}{str(incident_pk)}".encode()).hexdigest()


class IncidentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IncidentListView(generics.ListAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [AllowAny]
    pagination_class = IncidentPagination

    def get_queryset(self):
        cutoff = timezone.now() - timedelta(days=30)
        historical = self.request.query_params.get("historical")

        if historical == "true":
            # Only old resolved incidents (seeded/historical data)
            qs = Incident.objects.filter(status="RESOLVED", created_at__lt=cutoff)
        else:
            qs = Incident.objects.filter(
                status__in=["VERIFIED", "RESPONDING", "AGENCY_NOTIFIED", "RESOLVED"]
            )
            if historical == "false":
                # Exclude old resolved - live feed only
                qs = qs.exclude(status="RESOLVED", created_at__lt=cutoff)

        if zone := self.request.query_params.get("zone_name"):
            qs = qs.filter(zone_name__icontains=zone)
        if s := self.request.query_params.get("status"):
            qs = qs.filter(status=s)
        if t := self.request.query_params.get("incident_type"):
            qs = qs.filter(incident_type=t)
        if sev := self.request.query_params.get("severity"):
            qs = qs.filter(severity=sev)
        if yr_from := self.request.query_params.get("year_from"):
            qs = qs.filter(created_at__year__gte=int(yr_from))
        if yr_to := self.request.query_params.get("year_to"):
            qs = qs.filter(created_at__year__lte=int(yr_to))
        return qs


@api_view(["GET"])
@permission_classes([AllowAny])
def active_incidents(request):
    qs = Incident.objects.filter(status__in=["VERIFIED", "RESPONDING", "AGENCY_NOTIFIED"])
    return Response(IncidentSerializer(qs, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def incident_detail(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    return Response(IncidentDetailSerializer(incident).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def incident_track(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    latest_log = incident.response_logs.last()
    return Response({
        "id": str(incident.id),
        "status": incident.status,
        "incident_type": incident.incident_type,
        "severity": incident.severity,
        "address_text": incident.address_text,
        "zone_name": incident.zone_name,
        "vouch_count": incident.vouch_count,
        "total_donations_naira": incident.total_donations_naira,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
        "latest_log": {
            "to_status": latest_log.to_status,
            "note": latest_log.note,
            "actor": latest_log.actor,
            "created_at": latest_log.created_at,
        } if latest_log else None,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def incident_vouch(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    session_hash = _session_hash(request, pk)
    if VouchRecord.objects.filter(incident=incident, session_hash=session_hash).exists():
        return Response({"error": "Already vouched"}, status=status.HTTP_400_BAD_REQUEST)
    VouchRecord.objects.create(
        incident=incident,
        session_hash=session_hash,
        voucher_lat=request.data.get("lat"),
        voucher_lng=request.data.get("lng"),
    )
    incident.vouch_count += 1
    incident.save(update_fields=["vouch_count"])
    return Response({"vouch_count": incident.vouch_count})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def incident_dispatch(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    from apps.incidents.tasks import _transition
    _transition(incident, "AGENCY_NOTIFIED", f"agency:{request.user}")
    incident.save()
    return Response({"status": incident.status})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def incident_resolve(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    from apps.incidents.tasks import _transition
    _transition(incident, "RESOLVED", f"agency:{request.user}")
    incident.resolved_at = timezone.now()
    incident.save()
    return Response({"status": incident.status})


@api_view(["GET"])
@permission_classes([AllowAny])
def list_media(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    return Response(IncidentMediaSerializer(incident.media.all(), many=True).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def upload_media(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    existing_count = incident.media.count()

    if existing_count >= MAX_MEDIA_PER_INCIDENT:
        return Response(
            {"error": f"Maximum {MAX_MEDIA_PER_INCIDENT} media files per incident."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    files = request.FILES.getlist("files")
    if not files and "file" in request.FILES:
        files = [request.FILES["file"]]
    if not files:
        return Response({"error": "No files provided."}, status=status.HTTP_400_BAD_REQUEST)

    slots_remaining = MAX_MEDIA_PER_INCIDENT - existing_count
    files = files[:slots_remaining]

    uploaded = []
    errors = []

    for f in files:
        try:
            from services.media_service import upload_incident_media
            result = upload_incident_media(f, pk)
            media = IncidentMedia.objects.create(
                incident=incident,
                media_type=result["media_type"],
                public_url=result["url"],
                storage_path=result["storage_path"],
                file_size=result["file_size_kb"] * 1024,
                uploaded_by_hash=_session_hash(request, pk),
            )
            uploaded.append({
                "id": media.id,
                "url": media.public_url,
                "media_type": media.media_type,
            })
        except Exception as exc:
            logger.error("Media upload failed for %s: %s", f.name, exc)
            errors.append({"file": f.name, "error": str(exc)})

    if not uploaded:
        return Response({"uploaded": [], "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
    if errors:
        return Response({"uploaded": uploaded, "errors": errors}, status=status.HTTP_207_MULTI_STATUS)
    return Response({"uploaded": uploaded, "errors": []}, status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([AllowAny])
def delete_media(request, pk, media_pk):
    incident = get_object_or_404(Incident, pk=pk)
    media = get_object_or_404(IncidentMedia, pk=media_pk, incident=incident)

    is_admin = bool(request.user and request.user.is_authenticated)
    if not is_admin:
        if media.uploaded_by_hash != _session_hash(request, pk):
            return Response(
                {"error": "Not authorised to delete this media."},
                status=status.HTTP_403_FORBIDDEN,
            )

    try:
        from services.media_service import delete_incident_media
        delete_incident_media(media.storage_path)
    except Exception as exc:
        logger.warning("Storage delete failed for %s: %s", media.storage_path, exc)

    media.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# -- Historical analytics views ------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def zone_history(request):
    zone_name = request.query_params.get("zone_name", "").strip()
    lat_str = request.query_params.get("lat")
    lng_str = request.query_params.get("lng")
    radius_km = float(request.query_params.get("radius_km", 3.0))

    # Must have either zone_name or lat+lng
    if not zone_name and not (lat_str and lng_str):
        return Response({"error": "zone_name or lat+lng is required"}, status=400)

    since_2010 = datetime(2010, 1, 1, tzinfo=dt_timezone.utc)
    now = timezone.now()

    if lat_str and lng_str:
        lat, lng = float(lat_str), float(lng_str)

        # Determine nearest Lagos zone to use for historical data (seeded incidents have
        # zone_name but NULL coordinates due to Nominatim geocoding limitations)
        ZONE_CENTROIDS = [
            ("Ikeja",           6.6018, 3.3515),
            ("Surulere",        6.5022, 3.3570),
            ("Lekki",           6.4698, 3.5852),
            ("Victoria Island", 6.4281, 3.4219),
            ("Ajah",            6.4694, 3.5985),
            ("Ikorodu",         6.6194, 3.5098),
            ("Badagry",         6.4186, 2.8815),
            ("Alimosho",        6.6105, 3.2630),
            ("Oshodi",          6.5572, 3.3498),
            ("Mushin",          6.5310, 3.3550),
            ("Agege",           6.6225, 3.3268),
            ("Kosofe",          6.5891, 3.3984),
            ("Apapa",           6.4499, 3.3632),
            ("Lagos Island",    6.4541, 3.3947),
            ("Yaba",            6.5022, 3.3784),
            ("Orile",           6.4789, 3.3568),
            ("Ojo",             6.4712, 3.1791),
            ("Ajegunle",        6.4802, 3.3572),
            ("Isale Eko",       6.4527, 3.3917),
            ("Festac",          6.4722, 3.2794),
            ("Ipaja",           6.6104, 3.2445),
            ("Egbeda",          6.5714, 3.2887),
            ("Ojodu",           6.6376, 3.3589),
            ("Gbagada",         6.5501, 3.3861),
            ("Maryland",        6.5639, 3.3558),
            ("Ketu",            6.5843, 3.3869),
            ("Mile 12",         6.6067, 3.3835),
            ("Iyana-Ipaja",     6.6017, 3.2644),
            ("Sangotedo",       6.4616, 3.6603),
            ("Epe",             6.5876, 3.9817),
            ("Magodo",          6.6174, 3.3835),
            ("Ogudu",           6.5696, 3.3941),
            ("Bariga",          6.5322, 3.3902),
            ("Shomolu",         6.5356, 3.3838),
            ("Abule-Egba",      6.6391, 3.2727),
            ("Dopemu",          6.6002, 3.2941),
            ("Ijora",           6.4568, 3.3597),
            ("Ejigbo",          6.5374, 3.3157),
        ]
        import math
        def _dist2(z): return (z[1]-lat)**2 + (z[2]-lng)**2
        nearest_zone = min(ZONE_CENTROIDS, key=_dist2)[0]

        # IDs with real coordinates within radius (NULL coords excluded to prevent false matches)
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute(
                """SELECT id FROM incidents_incident
                   WHERE location_lat IS NOT NULL AND location_lng IS NOT NULL
                   AND (6371 * acos(LEAST(1.0,
                       cos(radians(%s)) * cos(radians(location_lat)) *
                       cos(radians(location_lng) - radians(%s)) +
                       sin(radians(%s)) * sin(radians(location_lat))
                   ))) <= %s""",
                [lat, lng, lat, radius_km]
            )
            nearby_ids = [row[0] for row in cur.fetchall()]

        # Combine: coordinate-matched incidents + zone-name-matched historical incidents
        from django.db.models import Q
        filter_q = Q(id__in=nearby_ids) | Q(zone_name__icontains=nearest_zone)
        qs = Incident.objects.filter(filter_q, status="RESOLVED", created_at__gte=since_2010)
        all_zone = Incident.objects.filter(filter_q)
        display_zone = nearest_zone
    else:
        qs = Incident.objects.filter(
            zone_name__icontains=zone_name,
            status="RESOLVED",
            created_at__gte=since_2010,
        )
        all_zone = Incident.objects.filter(zone_name__icontains=zone_name)
        display_zone = zone_name

    total = qs.count()

    by_type = {}
    for row in qs.values("incident_type").annotate(cnt=Count("id")).order_by("-cnt"):
        by_type[row["incident_type"]] = row["cnt"]

    by_year_qs = (
        qs.annotate(year=ExtractYear("created_at"))
        .values("year")
        .annotate(cnt=Count("id"))
        .order_by("year")
    )
    by_year = [{"year": r["year"], "count": r["cnt"]} for r in by_year_qs]

    total_all = all_zone.count()
    resolved_all = all_zone.filter(status="RESOLVED").count()
    resolution_rate = round(resolved_all / total_all * 100, 1) if total_all else 0.0

    resolved_timed = list(all_zone.filter(status="RESOLVED", resolved_at__isnull=False)[:500])
    avg_minutes = None
    total_secs, sample_count = 0, 0
    for inc in resolved_timed:
        delta = (inc.resolved_at - inc.created_at).total_seconds()
        if delta > 0:
            total_secs += delta
            sample_count += 1
    if sample_count:
        avg_minutes = round(total_secs / sample_count / 60)

    last_12 = qs.filter(created_at__gte=now - timedelta(days=365)).count()
    prior_12 = qs.filter(
        created_at__gte=now - timedelta(days=730),
        created_at__lt=now - timedelta(days=365),
    ).count()
    if prior_12 == 0 or last_12 == prior_12:
        trend = "stable"
    elif last_12 < prior_12:
        trend = "improving"
    else:
        trend = "increasing"

    years_span = max(1, (now - since_2010).days / 365)

    # Generic "Lagos" incidents have no specific zone tag (RSS headlines that just say "Lagos").
    # Apportion them evenly across ~20 major zones so the score reflects real city-level risk.
    # This prevents zones with sparse specific data from falsely scoring near 100.
    generic_lagos_count = Incident.objects.filter(
        zone_name__in=["Lagos", "Lagos Mainland", ""],
        status="RESOLVED",
        created_at__gte=since_2010,
    ).count()
    lagos_zone_share = round(generic_lagos_count / 20)  # ~5% of citywide incidents per zone

    # Effective total for scoring = zone-specific documented + proportional citywide share
    effective_total = total + lagos_zone_share

    if effective_total == 0:
        zone_score = 95
    else:
        # Calibrated for Lagos: 3 incidents/year = moderate risk (~70 score)
        # At 1/yr → ~83, at 5/yr → ~55, at 10/yr → ~35
        per_year_eff = effective_total / years_span
        freq_penalty = min(70, per_year_eff * 8)
        crit_high = qs.filter(severity__in=["CRITICAL", "HIGH"]).count()
        sev_penalty = min(15, (crit_high / max(total, 1)) * 20)
        res_bonus = (resolution_rate / 100) * 10
        zone_score = int(max(20, min(95, round(95 - freq_penalty - sev_penalty + res_bonus))))

    recent_5 = IncidentSerializer(qs.order_by("-created_at")[:5], many=True).data

    return Response({
        "zone_name": display_zone,
        "total_incidents": total,
        "total_incidents_effective": effective_total,
        "by_type": by_type,
        "by_year": by_year,
        "resolution_rate": resolution_rate,
        "avg_resolution_minutes": avg_minutes,
        "trend": trend,
        "zone_score": zone_score,
        "recent_5": recent_5,
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def zone_stats(request):
    since_2010 = datetime(2010, 1, 1, tzinfo=dt_timezone.utc)
    rows = (
        Incident.objects.filter(status="RESOLVED", created_at__gte=since_2010)
        .values("zone_name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )
    return Response({r["zone_name"] or "Unknown": r["cnt"] for r in rows})
