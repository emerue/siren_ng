from django.contrib import admin
from .models import Responder, ResponderDispatch


@admin.register(Responder)
class ResponderAdmin(admin.ModelAdmin):
    list_display  = ['name', 'skill_category', 'status', 'zone_name', 'is_available', 'total_responses', 'created_at']
    list_filter   = ['status', 'skill_category', 'is_available']
    search_fields = ['name', 'zone_name']
    readonly_fields = ['id', 'phone_hash', 'created_at']
    actions = ['mark_verified', 'mark_suspended']

    def mark_verified(self, req, qs):
        qs.update(status='VERIFIED')
    mark_verified.short_description = 'Mark selected as Verified'

    def mark_suspended(self, req, qs):
        qs.update(status='SUSPENDED')
    mark_suspended.short_description = 'Mark selected as Suspended'


@admin.register(ResponderDispatch)
class ResponderDispatchAdmin(admin.ModelAdmin):
    list_display  = ['responder', 'incident', 'accepted', 'notified_at', 'on_scene_at', 'completed_at']
    list_filter   = ['accepted']
    readonly_fields = ['notified_at']
