import uuid
from django.db import models


# ── RESOURCE BOARD ────────────────────────────────────────────────────────────

RESOURCE_CATEGORIES = [
    ('TRANSPORT',  'Transport (car, bike, keke)'),
    ('EQUIPMENT',  'Equipment (ladder, generator, rope, torch)'),
    ('MEDICAL',    'Medical (first aid kit, stretcher, oxygen)'),
    ('FOOD_WATER', 'Food and Water'),
    ('MANPOWER',   'Manpower (extra hands needed)'),
    ('OTHER',      'Other'),
]

RESOURCE_STATUS = [
    ('NEEDED',  'Needed'),
    ('CLAIMED', 'Claimed'),
    ('ARRIVED', 'Arrived'),
]


class ResourceItem(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident     = models.ForeignKey('incidents.Incident', on_delete=models.CASCADE,
                     related_name='resources')
    category     = models.CharField(max_length=20, choices=RESOURCE_CATEGORIES)
    label        = models.CharField(max_length=200)
    status       = models.CharField(max_length=10, choices=RESOURCE_STATUS, default='NEEDED')

    suggested_by_hash   = models.CharField(max_length=64)
    suggested_by_name   = models.CharField(max_length=100, blank=True)
    suggested_via       = models.CharField(max_length=20,
                            choices=[('WEB', 'Web'), ('WHATSAPP', 'WhatsApp')],
                            default='WEB')

    confirmed_by_hash   = models.CharField(max_length=64, blank=True)
    confirmed_at        = models.DateTimeField(null=True, blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', 'category', 'created_at']

    def __str__(self):
        return f'{self.label} ({self.status}) — {self.incident_id}'


class ResourceClaim(models.Model):
    resource      = models.ForeignKey(ResourceItem, on_delete=models.CASCADE,
                      related_name='claims')
    claimer_hash  = models.CharField(max_length=64)
    claimer_name  = models.CharField(max_length=100, blank=True)
    claimer_phone = models.CharField(max_length=20, blank=True)
    claimed_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('resource', 'claimer_hash')


# ── DONATIONS ─────────────────────────────────────────────────────────────────

DONATION_FUND_CHOICES = [
    ('VICTIM',    'Victim Relief — goes to the affected person or family'),
    ('RESPONDER', 'First Responder Appreciation — split equally among responders on scene'),
    ('PLATFORM',  'Emergency Response Fund — keeps Siren running'),
]

DONATION_STATUS = [
    ('PENDING',  'Pending'),
    ('SUCCESS',  'Success'),
    ('FAILED',   'Failed'),
    ('REFUNDED', 'Refunded'),
]


class Donation(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident        = models.ForeignKey('incidents.Incident', on_delete=models.CASCADE,
                        related_name='donations')
    donor_name      = models.CharField(max_length=200, blank=True)
    donor_email     = models.EmailField(blank=True)
    donor_phone     = models.CharField(max_length=20, blank=True)
    amount_kobo     = models.PositiveIntegerField()
    fund_choice     = models.CharField(max_length=15, choices=DONATION_FUND_CHOICES)
    status          = models.CharField(max_length=10, choices=DONATION_STATUS, default='PENDING')

    paystack_reference   = models.CharField(max_length=200, unique=True)
    paystack_response    = models.JSONField(default=dict)
    recipient_subaccount = models.CharField(max_length=100, blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def amount_naira(self):
        return self.amount_kobo / 100
