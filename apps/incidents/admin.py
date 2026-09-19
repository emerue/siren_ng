import re

from django.contrib import admin, messages
from django.db.models import Count
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from django.conf import settings

from . import coordinator as coord
from .coordinator import is_coordinator, actor_name
from .models import Incident, ResponseLog, VouchRecord, IncidentMedia
from .forms import IncidentMediaAdminForm


# Fields a coordinator may edit. Everything else on their form is readonly, which
# means Django never binds it — a hand-crafted POST containing `status=RESOLVED`
# is dropped, not saved.
COORDINATOR_EDITABLE = ("incident_type", "severity", "zone_name", "coordinator_note")

COORDINATOR_FIELDSETS = (
    ("Report", {
        "fields": ("status_display", "age_display", "created_at",
                   "description", "reporter_phone_masked"),
    }),
    ("Your decision", {
        "fields": COORDINATOR_EDITABLE,
        "description": "Correct the classification if the AI got it wrong, then use "
                       "the buttons at the top of this page.",
    }),
    ("Location", {"fields": ("address_text", "lga", "location_display")}),
    ("AI suggestion — not a verification", {"fields": ("ai_suggestion_panel",)}),
)

COORDINATOR_READONLY = tuple(
    field
    for _, opts in COORDINATOR_FIELDSETS
    for field in opts["fields"]
    if field not in COORDINATOR_EDITABLE
)

# Identity fields a coordinator must never see. reporter_hash is excluded
# alongside the phone because it is sha256 over a ~13-digit keyspace — masking
# the number while publishing its hash would defeat the point.
IDENTITY_FIELDS = {"reporter_phone", "reporter_hash"}


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

    # ── Policy overrides ────────────────────────────────────────────────────
    # Each branches on is_coordinator and otherwise defers to super(), so the
    # superuser experience is byte-identical to before.

    def get_fieldsets(self, request, obj=None):
        if is_coordinator(request.user):
            return COORDINATOR_FIELDSETS
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if is_coordinator(request.user):
            return COORDINATOR_READONLY
        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request):
        if is_coordinator(request.user):
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        if is_coordinator(request.user):
            return False
        return super().has_delete_permission(request, obj)

    def get_inlines(self, request, obj=None):
        # Media is shown as a read-only thumbnail strip in the custom template.
        # The upload inline is hostile on a phone and would let a coordinator
        # delete evidence.
        if is_coordinator(request.user):
            return []
        return super().get_inlines(request, obj)

    def get_actions(self, request):
        # No bulk actions for coordinators: every confirm must pass through the
        # interstitial, and run_ai_verification spends money per click.
        if is_coordinator(request.user):
            return {}
        return super().get_actions(request)

    def lookup_allowed(self, lookup, value, request=None):
        # ModelAdmin.lookup_allowed permits any local-field lookup, which would
        # turn the changelist into a phone-number oracle
        # (?reporter_phone__startswith=+23480...). Deny it outright.
        if request is not None and is_coordinator(request.user):
            if lookup.split("__")[0] in IDENTITY_FIELDS:
                return False
        return super().lookup_allowed(lookup, value, request)

    def get_list_display(self, request):
        if is_coordinator(request.user):
            # Five short columns. This — not CSS — is what keeps the queue
            # readable at 360px without horizontal scroll.
            return ["age_display", "severity_pill", "incident_type",
                    "zone_name", "media_marker"]
        return super().get_list_display(request)

    def get_list_filter(self, request):
        if is_coordinator(request.user):
            return ["status", "severity", "incident_type", "lga"]
        return super().get_list_filter(request)

    def get_ordering(self, request):
        if is_coordinator(request.user):
            return ["created_at"]  # oldest first: this is an SLA queue, not a feed
        return super().get_ordering(request)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if is_coordinator(request.user):
            return qs.annotate(_media_count=Count("media"))
        return qs

    # ── Display helpers ─────────────────────────────────────────────────────

    @admin.display(description="Waiting", ordering="created_at")
    def age_display(self, obj):
        minutes = int((timezone.now() - obj.created_at).total_seconds() // 60)
        sla = getattr(settings, "COORDINATOR_SLA_MINUTES", 10)
        if minutes < sla / 2:
            level = "ok"
        elif minutes < sla:
            level = "warn"
        else:
            level = "late"
        if minutes < 60:
            label = f"{minutes} min"
        elif minutes < 1440:
            label = f"{minutes // 60}h {minutes % 60}m"
        else:
            label = f"{minutes // 1440}d"
        return format_html('<span class="siren-age siren-age--{}">{}</span>', level, label)

    @admin.display(description="Severity", ordering="severity")
    def severity_pill(self, obj):
        level = (obj.severity or "LOW").lower()
        return format_html('<span class="siren-pill siren-pill--{}">{}</span>',
                           level, obj.severity or "—")

    @admin.display(description="📷")
    def media_marker(self, obj):
        count = getattr(obj, "_media_count", None)
        if count is None:
            count = obj.media.count()
        if not count:
            return ""
        return format_html('<span class="siren-media" title="{} attachment(s)">📷 {}</span>',
                           count, count)

    @admin.display(description="Status")
    def status_display(self, obj):
        return format_html('<span class="siren-status">{}</span>', obj.status)

    @admin.display(description="Reporter")
    def reporter_phone_masked(self, obj):
        """Last four digits only. The full number is never rendered."""
        digits = re.sub(r"\D", "", obj.reporter_phone or "")
        if not digits:
            return "—"
        return format_html('<span class="siren-masked">••••{}</span>', digits[-4:])

    @admin.display(description="Where")
    def location_display(self, obj):
        if obj.location_lat and obj.location_lng:
            return format_html(
                '{} <a href="https://maps.google.com/?q={},{}" target="_blank" '
                'rel="noopener noreferrer">Open in Maps ↗</a>',
                obj.zone_name or "", obj.location_lat, obj.location_lng,
            )
        return obj.zone_name or obj.address_text or "—"

    @admin.display(description="AI suggestion")
    def ai_suggestion_panel(self, obj):
        """Built with format_html placeholders only.

        ai_raw_response holds attacker-influenced text (zone_name is truncated by
        _validate_ai_result but not sanitised), so this must never be mark_safe'd.
        """
        raw = obj.ai_raw_response if isinstance(obj.ai_raw_response, dict) else {}
        rows = [
            ("Type", raw.get("incident_type") or "—"),
            ("Severity", raw.get("severity") or "—"),
            ("Area", raw.get("zone_name") or "—"),
            ("Confidence", f"{(obj.ai_confidence or 0) * 100:.0f}%"),
            ("Fraud score", f"{(obj.fraud_score or 0):.2f}"),
        ]
        body = format_html_join(
            "", "<div class='siren-ai__row'><dt>{}</dt><dd>{}</dd></div>", rows
        )
        return format_html(
            "<div class='siren-ai'><p class='siren-ai__caption'>A classification hint, "
            "not a verification. Nothing is sent until you confirm.</p><dl>{}</dl></div>",
            body,
        )

    # ── Views ───────────────────────────────────────────────────────────────

    def changelist_view(self, request, extra_context=None):
        if is_coordinator(request.user) and not request.META.get("QUERY_STRING"):
            # Land on the work: reports actually awaiting a decision.
            return HttpResponseRedirect(f"{request.path}?status__exact=DETECTED")
        context = {
            **(extra_context or {}),
            "is_coordinator": is_coordinator(request.user),
            "sla_minutes": getattr(settings, "COORDINATOR_SLA_MINUTES", 10),
            "refresh_seconds": 30,
        }
        return super().changelist_view(request, context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        context = {**(extra_context or {}), "is_coordinator": is_coordinator(request.user)}
        if context["is_coordinator"]:
            incident = self.get_object(request, object_id)
            if incident is not None:
                context.update({
                    "incident": incident,
                    "rejection_reasons": coord.REJECTION_REASONS,
                    "can_confirm": coord.can_confirm(incident),
                    "can_reject": coord.can_reject(incident),
                    "can_resolve": coord.can_resolve(incident),
                    "can_request_info": coord.can_request_info(incident),
                    "within_service_window": coord.within_service_window(incident),
                    "reply_capture_enabled": settings.FEATURES.get(
                        "reporter_reply_capture", False),
                    "media_items": list(incident.media.all()),
                    "timeline": list(incident.response_logs.all().order_by("-created_at")),
                })
        return super().change_view(request, object_id, form_url, context)

    # ── Custom action URLs ──────────────────────────────────────────────────

    def get_urls(self):
        custom = [
            path("<path:object_id>/coordinator/confirm/",
                 self.admin_site.admin_view(self.coordinator_confirm_view),
                 name="incidents_incident_coordinator_confirm"),
            path("<path:object_id>/coordinator/reject/",
                 self.admin_site.admin_view(self.coordinator_reject_view),
                 name="incidents_incident_coordinator_reject"),
            path("<path:object_id>/coordinator/resolve/",
                 self.admin_site.admin_view(self.coordinator_resolve_view),
                 name="incidents_incident_coordinator_resolve"),
            path("<path:object_id>/coordinator/request-info/",
                 self.admin_site.admin_view(self.coordinator_request_info_view),
                 name="incidents_incident_coordinator_request_info"),
        ]
        # MUST precede super(): ModelAdmin.get_urls ends in a greedy
        # `<path:object_id>/` redirect that would otherwise swallow these.
        return custom + super().get_urls()

    def _action_target(self, request, object_id):
        """Shared guard. admin_view only checks is_staff, never model permissions."""
        incident = get_object_or_404(Incident, pk=object_id)
        if not self.has_change_permission(request, incident):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return incident

    def _back(self, object_id):
        return HttpResponseRedirect(
            reverse("admin:incidents_incident_change", args=[object_id])
        )

    def coordinator_confirm_view(self, request, object_id):
        incident = self._action_target(request, object_id)

        if request.method == "GET":
            # The interstitial. A GET must never broadcast.
            return TemplateResponse(
                request,
                "admin/incidents/incident/coordinator_confirm.html",
                {**self.admin_site.each_context(request),
                 "opts": self.model._meta,
                 "incident": incident,
                 "lga": incident.zone_name or incident.lga or "this area",
                 "title": "Confirm and alert"},
            )
        if request.method != "POST":
            return HttpResponseNotAllowed(["GET", "POST"])

        if coord.confirm_and_alert(incident.pk, actor_name(request)):
            self.message_user(
                request,
                f"Confirmed. Subscribers in {incident.zone_name or 'the area'} are being alerted.",
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                f"No action taken — this incident is already {incident.status}.",
                messages.WARNING,
            )
        return self._back(object_id)

    def coordinator_reject_view(self, request, object_id):
        incident = self._action_target(request, object_id)

        if request.method == "GET":
            return TemplateResponse(
                request,
                "admin/incidents/incident/coordinator_reject.html",
                {**self.admin_site.each_context(request),
                 "opts": self.model._meta,
                 "incident": incident,
                 "rejection_reasons": coord.REJECTION_REASONS,
                 "title": "Reject report"},
            )
        if request.method != "POST":
            return HttpResponseNotAllowed(["GET", "POST"])

        try:
            done = coord.reject(incident.pk, actor_name(request),
                                request.POST.get("reason", ""))
        except ValueError:
            self.message_user(request, "Choose a reason from the list.", messages.ERROR)
            return self._back(object_id)

        self.message_user(
            request,
            "Rejected. The reporter has been told." if done
            else f"No action taken — this incident is already {incident.status}.",
            messages.SUCCESS if done else messages.WARNING,
        )
        return self._back(object_id)

    def coordinator_resolve_view(self, request, object_id):
        incident = self._action_target(request, object_id)
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        done = coord.resolve(incident.pk, actor_name(request))
        self.message_user(
            request,
            "Resolved. The reporter has been told." if done
            else f"No action taken — this incident is {incident.status}.",
            messages.SUCCESS if done else messages.WARNING,
        )
        return self._back(object_id)

    def coordinator_request_info_view(self, request, object_id):
        incident = self._action_target(request, object_id)
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        done = coord.request_more_info(incident.pk, actor_name(request))
        self.message_user(
            request,
            "Asked the reporter for more detail." if done
            else "Not sent — already asked recently, or the reporter cannot be "
                 "messaged (no number, or outside the 24-hour WhatsApp window).",
            messages.SUCCESS if done else messages.WARNING,
        )
        return self._back(object_id)

    # ── Bulk actions (superusers) ───────────────────────────────────────────
    # Delegated to the service layer so they get the same idempotency guards and
    # record the real username instead of the literal string "admin".

    @admin.action(permissions=["change"],
                  description="Mark selected as VERIFIED (with audit log)")
    def mark_verified(self, req, qs):
        actor = actor_name(req)
        done = sum(1 for incident in qs if coord.confirm_and_alert(incident.pk, actor))
        if req is not None:
            self.message_user(req, f"Confirmed and alerted for {done} incident(s).")

    @admin.action(permissions=["change"],
                  description="Mark selected as RESOLVED (with audit log)")
    def mark_resolved(self, req, qs):
        actor = actor_name(req)
        done = sum(1 for incident in qs if coord.resolve(incident.pk, actor))
        if req is not None:
            self.message_user(req, f"Resolved {done} incident(s).")

    @admin.action(permissions=["change"],
                  description="Mark selected as REJECTED (with audit log)")
    def mark_rejected(self, req, qs):
        actor = actor_name(req)
        done = sum(1 for incident in qs
                   if coord.reject(incident.pk, actor, "UNINTELLIGIBLE"))
        if req is not None:
            self.message_user(req, f"Rejected {done} incident(s).")

    @admin.action(permissions=["change"],
                  description="Run AI verification on selected incidents")
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
        if req is not None:
            self.message_user(req, f"AI verification queued/run for {count} incident(s).")


@admin.register(ResponseLog)
class ResponseLogAdmin(admin.ModelAdmin):
    list_display    = ["incident", "from_status", "to_status", "actor", "created_at"]
    readonly_fields = ["incident", "from_status", "to_status", "actor", "note", "created_at"]

    def has_add_permission(self, request):
        return False if is_coordinator(request.user) else super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False if is_coordinator(request.user) else super().has_delete_permission(request, obj)


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

    def get_model_perms(self, request):
        # Coordinators need view_incidentmedia to see thumbnails, but the model
        # should not get its own row on the admin index. get_model_perms is
        # consulted only when building that index.
        if is_coordinator(request.user):
            return {}
        return super().get_model_perms(request)
