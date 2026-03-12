from django.contrib import admin
from .models import Incident, ResponseLog, VouchRecord


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display  = ['id', 'incident_type', 'severity', 'status', 'zone_name',
                     'vouch_count', 'ai_confidence', 'fraud_score',
                     'total_donations_kobo', 'created_at']
    list_filter   = ['status', 'incident_type', 'severity', 'source']
    search_fields = ['description', 'address_text', 'zone_name']
    ordering      = ['-created_at']
    readonly_fields = ['id', 'reporter_hash', 'ai_raw_response', 'media_urls', 'created_at', 'updated_at']
    actions       = ['mark_verified', 'mark_resolved', 'mark_rejected']

    def mark_verified(self, req, qs): qs.update(status='VERIFIED')
    def mark_resolved(self, req, qs): qs.update(status='RESOLVED')
    def mark_rejected(self, req, qs): qs.update(status='REJECTED')


@admin.register(ResponseLog)
class ResponseLogAdmin(admin.ModelAdmin):
    list_display    = ['incident', 'from_status', 'to_status', 'actor', 'created_at']
    readonly_fields = ['incident', 'from_status', 'to_status', 'actor', 'note', 'created_at']


@admin.register(VouchRecord)
class VouchRecordAdmin(admin.ModelAdmin):
    list_display = ['incident', 'session_hash', 'source', 'is_suspicious', 'created_at']
    list_filter  = ['source', 'is_suspicious']
