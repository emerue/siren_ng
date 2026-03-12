import uuid
from django.db import models


class Organisation(models.Model):
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name             = models.CharField(max_length=300)
    org_type         = models.CharField(max_length=20, choices=[
                         ('HOSPITAL','Hospital/Clinic'),
                         ('AMBULANCE','Ambulance Service'),
                         ('PHARMACY','Pharmacy'),
                         ('TOWING','Towing/Heavy Equipment'),
                         ('FIRE_SAFETY','Fire Safety Company'),
                         ('NGO','NGO/Community Group'),
                         ('AGENCY','Government Agency'),
                         ('OTHER','Other'),
                       ])
    status           = models.CharField(max_length=15,
                         choices=[('PENDING','Pending'),('VERIFIED','Verified'),
                                  ('SUSPENDED','Suspended')],
                         default='PENDING')
    location_lat     = models.FloatField()
    location_lng     = models.FloatField()
    address          = models.CharField(max_length=500)
    zone_name        = models.CharField(max_length=100, blank=True)
    response_radius_km = models.FloatField(default=5.0)
    contact_name     = models.CharField(max_length=200)
    contact_whatsapp = models.CharField(max_length=20)
    contact_phone    = models.CharField(max_length=20, blank=True)
    responds_to      = models.JSONField(default=list)
    operating_hours  = models.CharField(max_length=200, default='24/7')
    cac_number       = models.CharField(max_length=100, blank=True)
    total_responses  = models.PositiveIntegerField(default=0)
    dashboard_user   = models.OneToOneField('auth.User', null=True, blank=True,
                         on_delete=models.SET_NULL, related_name='organisation')
    created_at       = models.DateTimeField(auto_now_add=True)
