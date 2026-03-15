import uuid
from django.db import models


class SkillCategory(models.TextChoices):
    MEDICAL_ADVANCED = 'MED_ADV',    'Medical Advanced (Doctor/Surgeon)'
    MEDICAL_BASIC    = 'MED_BASIC',  'Medical Basic (Nurse/Paramedic)'
    FIRE_RESPONSE    = 'FIRE',       'Fire Response'
    WATER_RESCUE     = 'WATER',      'Water/Flood Rescue'
    STRUCTURAL       = 'STRUCTURAL', 'Structural Rescue/Engineer'
    ELECTRICAL       = 'ELECTRICAL', 'Electrical (Licensed)'
    FIRST_AID        = 'FIRST_AID',  'First Aid/CPR Certified'


class Responder(models.Model):
    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name               = models.CharField(max_length=200)
    phone_hash         = models.CharField(max_length=64, unique=True)
    whatsapp_number    = models.CharField(max_length=20)  # E.164: +2348012345678
    skill_category     = models.CharField(max_length=20, choices=SkillCategory.choices)
    status             = models.CharField(max_length=15,
                           choices=[('PENDING','Pending'),('VERIFIED','Verified'),
                                    ('SUSPENDED','Suspended')],
                           default='PENDING')
    licence_number     = models.CharField(max_length=100, blank=True)
    home_lat           = models.FloatField()
    home_lng           = models.FloatField()
    response_radius_km = models.FloatField(default=2.0)
    is_available       = models.BooleanField(default=False)
    responds_to        = models.JSONField(default=list)  # List of IncidentType values
    total_responses    = models.PositiveIntegerField(default=0)
    zone_name          = models.CharField(max_length=100, blank=True)

    # Paystack sub-account for receiving appreciation donations
    paystack_subaccount = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.skill_category})"


class ResponderDispatch(models.Model):
    """Every notification sent to a responder for an incident."""
    responder    = models.ForeignKey(Responder, on_delete=models.CASCADE,
                     related_name='dispatches')
    incident     = models.ForeignKey('incidents.Incident', on_delete=models.CASCADE,
                     related_name='responder_dispatches')
    notified_at  = models.DateTimeField(auto_now_add=True)
    accepted     = models.BooleanField(null=True)  # None=pending True=yes False=no
    on_scene_at  = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('responder', 'incident')
