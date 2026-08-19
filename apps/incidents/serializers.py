from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Incident, ResponseLog, VouchRecord, IncidentMedia


def _resolved_to_closed(obj):
    if obj.status == "RESOLVED":
        cutoff = timezone.now() - timedelta(days=30)
        if obj.created_at < cutoff:
            return "CLOSED"
    return obj.status


# ── Field allowlists ──────────────────────────────────────────────────────────
#
# SECURITY: these serializers previously used `fields = "__all__"`, which
# published `reporter_phone` (raw Twilio WhatsApp identity), `reporter_hash`,
# and the internal AI payload on PUBLIC, unauthenticated endpoints
# (/api/incidents/, /api/incidents/active/, /api/incidents/<id>/).
#
# BRD §7 security invariant: reporter_phone must NEVER appear in API responses.
# We now allowlist fields explicitly. Adding a sensitive field to the model can
# no longer leak it by default — it has to be added here deliberately.
#
# NEVER add to any serializer below: reporter_phone, reporter_hash.

PUBLIC_INCIDENT_FIELDS = [
    "id",
    "source",
    "incident_type",
    "description",
    "severity",
    "status",
    "location_lat",
    "location_lng",
    "address_text",
    "zone_name",
    "lga",
    "is_historical",
    "verified",
    "source_url",
    "date_occurred",
    "affected_count",
    "casualties",
    "injuries",
    "media_urls",
    "vouch_count",
    "vouch_threshold",
    "total_donations_kobo",
    "total_donations_naira",
    "donation_count",
    "is_infrastructure",
    "created_at",
    "updated_at",
    "resolved_at",
]

# Coordinator-only triage signals. Still excludes reporter identity entirely.
STAFF_ONLY_INCIDENT_FIELDS = ["ai_confidence", "fraud_score", "ai_raw_response"]


class ResponseLogSerializer(serializers.ModelSerializer):
    """Public timeline entry. `note` and `actor` are withheld — notes carry
    internal triage reasoning and actor identifies the coordinator."""

    class Meta:
        model = ResponseLog
        fields = ["id", "from_status", "to_status", "created_at"]


class StaffResponseLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseLog
        fields = ["id", "from_status", "to_status", "actor", "note", "created_at"]


class IncidentMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentMedia
        fields = ["id", "media_type", "public_url", "file_size", "caption", "upload_timestamp"]


class IncidentSerializer(serializers.ModelSerializer):
    """PUBLIC incident representation."""

    total_donations_naira = serializers.FloatField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return _resolved_to_closed(obj)

    class Meta:
        model = Incident
        fields = PUBLIC_INCIDENT_FIELDS
        read_only_fields = PUBLIC_INCIDENT_FIELDS


class IncidentDetailSerializer(IncidentSerializer):
    """PUBLIC incident detail — adds media and a redacted timeline."""

    response_logs = ResponseLogSerializer(many=True, read_only=True)
    media = IncidentMediaSerializer(many=True, read_only=True)

    class Meta(IncidentSerializer.Meta):
        fields = PUBLIC_INCIDENT_FIELDS + ["response_logs", "media"]


class IncidentStaffSerializer(IncidentDetailSerializer):
    """Authenticated coordinator view: adds AI triage signals and full logs.

    Reporter phone/hash remain excluded — the coordinator reaches the reporter
    through the messaging pipeline, never by reading the number out of an API.
    """

    response_logs = StaffResponseLogSerializer(many=True, read_only=True)

    class Meta(IncidentDetailSerializer.Meta):
        fields = PUBLIC_INCIDENT_FIELDS + [
            "response_logs",
            "media",
        ] + STAFF_ONLY_INCIDENT_FIELDS
