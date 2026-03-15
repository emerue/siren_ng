from django.contrib import admin
from .models import ResourceItem, ResourceClaim, Donation


@admin.register(ResourceItem)
class ResourceItemAdmin(admin.ModelAdmin):
    list_display = ['label', 'category', 'status', 'incident', 'created_at']
    list_filter  = ['status', 'category']
    actions      = ['mark_arrived']

    def mark_arrived(self, req, qs):
        from django.utils import timezone
        qs.update(status='ARRIVED', confirmed_at=timezone.now())
    mark_arrived.short_description = 'Mark selected as Arrived'


@admin.register(ResourceClaim)
class ResourceClaimAdmin(admin.ModelAdmin):
    list_display = ['resource', 'claimer_name', 'claimer_phone', 'claimed_at']
    readonly_fields = ['claimed_at']


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display    = ['incident', 'donor_name', 'amount_kobo', 'fund_choice', 'status', 'created_at']
    list_filter     = ['status', 'fund_choice']
    readonly_fields = ['paystack_reference', 'paystack_response', 'created_at']
