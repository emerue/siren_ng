from django.contrib import admin
from .models import LocationSubscription, SubscriptionAlert, SafetyScoreLog


@admin.register(LocationSubscription)
class LocationSubscriptionAdmin(admin.ModelAdmin):
    list_display  = ['label', 'subscription_type', 'location_type', 'safety_score',
                     'alert_radius_km', 'is_active', 'created_at']
    list_filter   = ['subscription_type', 'location_type', 'is_active']
    search_fields = ['label', 'whatsapp_number']
    readonly_fields = ['id', 'phone_hash', 'created_at', 'updated_at']


@admin.register(SubscriptionAlert)
class SubscriptionAlertAdmin(admin.ModelAdmin):
    list_display  = ['subscription', 'incident', 'distance_km', 'alert_type', 'sent_at', 'delivered']
    list_filter   = ['delivered', 'alert_type']
    readonly_fields = ['sent_at']


@admin.register(SafetyScoreLog)
class SafetyScoreLogAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'score', 'created_at']
    readonly_fields = ['subscription', 'score', 'reason', 'created_at']
