from django.contrib import admin
from .models import Incident, ResponseLog, VouchRecord, IncidentMedia
from .forms import IncidentMediaAdminForm


class IncidentMediaInline(admin.StackedInline):
    model = IncidentMedia
    form = IncidentMediaAdminForm
    extra = 1
    can_delete = True
    readonly_fields = ["public_url", "storage_path", "file_size", "uploaded_by_hash", "upload_timestamp"]
    fields = [
        "upload_file",
        "external_url",
        "media_type",
        "caption",
        "public_url",
        "storage_path",
        "file_size",
        "upload_timestamp",
    ]


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    inlines = [IncidentMediaInline]
    list_display  = ["id", "incident_type", "severity", "status", "lga", "zone_name",
                     "is_historical", "verified", "date_occurred",
                     "vouch_count", "ai_confidence", "created_at"]
    list_filter   = ["status", "incident_type", "severity", "source",
                     "is_historical", "verified", "is_infrastructure", "lga"]
    search_fields = ["description", "address_text", "zone_name", "lga", "source_url"]
    ordering      = ["-created_at"]
    readonly_fields = ["id", "reporter_hash", "ai_raw_response", "media_urls", "created_at", "updated_at"]
    actions       = ["mark_verified", "mark_resolved", "mark_rejected", "run_ai_verification"]

    def mark_verified(self, req, qs):
        from .tasks import _transition
        for incident in qs:
            if incident.status != "VERIFIED":
                _transition(incident, "VERIFIED", "admin", "Manually verified via admin panel")
                incident.save()
    mark_verified.short_description = "Mark selected as VERIFIED (with audit log)"

    def mark_resolved(self, req, qs):
        from .tasks import _transition
        for incident in qs:
            if incident.status != "RESOLVED":
                _transition(incident, "RESOLVED", "admin", "Resolved via admin panel")
                incident.save()
    mark_resolved.short_description = "Mark selected as RESOLVED (with audit log)"

    def mark_rejected(self, req, qs):
        from .tasks import _transition
        for incident in qs:
            if incident.status != "REJECTED":
                _transition(incident, "REJECTED", "admin", "Rejected via admin panel")
                incident.save()
    mark_rejected.short_description = "Mark selected as REJECTED (with audit log)"

    def run_ai_verification(self, req, qs):
        from .tasks import verify_incident_ai
        count = 0
        for incident in qs:
            try:
                verify_incident_ai.delay(str(incident.id))
                count += 1
            except Exception:
                verify_incident_ai(str(incident.id))
                count += 1
        self.message_user(req, f"AI verification queued/run for {count} incident(s).")
    run_ai_verification.short_description = "Run AI verification on selected incidents"


@admin.register(ResponseLog)
class ResponseLogAdmin(admin.ModelAdmin):
    list_display    = ["incident", "from_status", "to_status", "actor", "created_at"]
    readonly_fields = ["incident", "from_status", "to_status", "actor", "note", "created_at"]


@admin.register(VouchRecord)
class VouchRecordAdmin(admin.ModelAdmin):
    list_display = ["incident", "session_hash", "source", "is_suspicious", "created_at"]
    list_filter  = ["source", "is_suspicious"]


@admin.register(IncidentMedia)
class IncidentMediaAdmin(admin.ModelAdmin):
    list_display   = ["id", "incident", "media_type", "file_size", "upload_timestamp"]
    list_filter    = ["media_type"]
    readonly_fields = ["incident", "media_type", "public_url", "storage_path",
                       "file_size", "uploaded_by_hash", "upload_timestamp"]
    search_fields  = ["incident__id", "storage_path"]
    ordering       = ["-upload_timestamp"]
