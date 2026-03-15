from django.contrib import admin
from .models import Organisation


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'org_type', 'status', 'zone_name', 'total_responses', 'created_at']
    list_filter   = ['status', 'org_type']
    search_fields = ['name', 'zone_name', 'contact_name']
    readonly_fields = ['id', 'created_at']
    actions = ['mark_verified', 'mark_suspended']

    def mark_verified(self, req, qs):
        qs.update(status='VERIFIED')
    mark_verified.short_description = 'Mark selected as Verified'

    def mark_suspended(self, req, qs):
        qs.update(status='SUSPENDED')
    mark_suspended.short_description = 'Mark selected as Suspended'
