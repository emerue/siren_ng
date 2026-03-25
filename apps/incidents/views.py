import hashlib
import logging

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
        qs = Incident.objects.filter(
            status__in=["VERIFIED", "RESPONDING", "AGENCY_NOTIFIED", "RESOLVED"]
        )
        if zone := self.request.query_params.get("zone_name"):
            qs = qs.filter(zone_name=zone)
        if s := self.request.query_params.get("status"):
            qs = qs.filter(status=s)
        if t := self.request.query_params.get("incident_type"):
            qs = qs.filter(incident_type=t)
        if sev := self.request.query_params.get("severity"):
            qs = qs.filter(severity=sev)
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
