import uuid
from django.db import models

LOCATION_TYPES = [
    ('HOME',   'Home'),
    ('SCHOOL', 'School/Child location'),
    ('LAND',   'Land/Property'),
    ('OFFICE', 'Office/Workplace'),
    ('FAMILY', 'Family member location'),
    ('OTHER',  'Other'),
]


class LocationSubscription(models.Model):
    """
    A saved location (or commute corridor) the subscriber wants monitored.

    POINT:   Single location. Alert when incident within alert_radius_km.
    COMMUTE: Home + Office. Alert when incident within 1.5km of route
             corridor during peak hours (6-10am, 4-8pm Lagos time).
    """
    SUBSCRIPTION_TYPES = [
        ('POINT',   'Single Point — Guardian Mode'),
        ('COMMUTE', 'Commute Shield — Home + Office corridor'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_hash       = models.CharField(max_length=64)
    whatsapp_number  = models.CharField(max_length=20)
    label            = models.CharField(max_length=200)

    subscription_type = models.CharField(max_length=10, choices=SUBSCRIPTION_TYPES,
                          default='POINT')
    location_type    = models.CharField(max_length=10, choices=LOCATION_TYPES, default='HOME')

    # Home or single-point location
    location_lat     = models.FloatField()
    location_lng     = models.FloatField()

    # COMMUTE only — second pin (office)
    office_lat       = models.FloatField(null=True, blank=True)
    office_lng       = models.FloatField(null=True, blank=True)

    # Guardian Mode — list of family/property labels saved under this subscriber
    # e.g. ["Timi (school)", "Mama (Ikeja)", "Shop (Alimosho)"]
    family_members   = models.JSONField(default=list)

    alert_radius_km  = models.FloatField(default=1.0)   # for POINT subscriptions
    commute_buffer_km = models.FloatField(default=1.5)  # for COMMUTE corridor checks
    peak_only        = models.BooleanField(default=False) # auto True for COMMUTE

    is_active        = models.BooleanField(default=True)
    incident_types   = models.JSONField(default=list)   # empty = all types

    # Safety Score: 0-100. Updated daily at 6am by celery-beat task.
    # Based on incident frequency near this location in the past 30 days.
    safety_score     = models.IntegerField(default=85)

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['label']

    def __str__(self):
        return f"{self.label} ({self.whatsapp_number})"


class SubscriptionAlert(models.Model):
    """Prevents duplicate alerts per subscription + incident pair."""
    subscription = models.ForeignKey(LocationSubscription, on_delete=models.CASCADE,
                     related_name='alerts')
    incident     = models.ForeignKey('incidents.Incident', on_delete=models.CASCADE,
                     related_name='subscription_alerts')
    distance_km  = models.FloatField()
    alert_type   = models.CharField(max_length=10,
                     choices=[('POINT','Point'),('COMMUTE','Commute')], default='POINT')
    sent_at      = models.DateTimeField(auto_now_add=True)
    delivered    = models.BooleanField(default=True)

    class Meta:
        unique_together = ('subscription', 'incident')


class SafetyScoreLog(models.Model):
    """
    Daily safety score history for a subscription location.
    Kept for 90 days. Used in /my-impact chart.
    """
    subscription = models.ForeignKey(LocationSubscription, on_delete=models.CASCADE,
                     related_name='score_logs')
    score        = models.IntegerField()       # 0-100
    reason       = models.TextField(blank=True) # e.g. "2 HAZARD incidents within 1km this week"
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
