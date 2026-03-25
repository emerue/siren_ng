import uuid
from django.db import models


class IncidentType(models.TextChoices):
    FIRE      = 'FIRE',      'Fire Outbreak'
    FLOOD     = 'FLOOD',     'Flooding'
    COLLAPSE  = 'COLLAPSE',  'Building/Structural Collapse'
    RTA       = 'RTA',       'Road Traffic Accident'
    EXPLOSION = 'EXPLOSION', 'Gas/Chemical Explosion'
    DROWNING  = 'DROWNING',  'Drowning/Water Emergency'
    HAZARD    = 'HAZARD',    'Structural/Electrical Hazard'


class IncidentSeverity(models.TextChoices):
    LOW      = 'LOW',      'Low'
    MEDIUM   = 'MEDIUM',   'Medium'
    HIGH     = 'HIGH',     'High'
    CRITICAL = 'CRITICAL', 'Critical'


class IncidentStatus(models.TextChoices):
    DETECTED        = 'DETECTED',        'Detected'
    VERIFYING       = 'VERIFYING',       'Verifying'
    VERIFIED        = 'VERIFIED',        'Verified'
    RESPONDING      = 'RESPONDING',      'Community Responding'
    AGENCY_NOTIFIED = 'AGENCY_NOTIFIED', 'Agency Notified'
    RESOLVED        = 'RESOLVED',        'Resolved'
    REJECTED        = 'REJECTED',        'Rejected'


class Incident(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source        = models.CharField(max_length=20,
                      choices=[('WHATSAPP', 'WhatsApp'), ('WEB', 'Web Portal')])
    external_id   = models.CharField(max_length=200, blank=True)
    reporter_hash = models.CharField(max_length=64)
    reporter_phone = models.CharField(max_length=20, blank=True)

    incident_type = models.CharField(max_length=20, choices=IncidentType.choices, blank=True)
    description   = models.TextField()
    severity      = models.CharField(max_length=10, choices=IncidentSeverity.choices,
                      default='MEDIUM')
    status        = models.CharField(max_length=20, choices=IncidentStatus.choices,
                      default='DETECTED')

    location_lat  = models.FloatField(null=True, blank=True)
    location_lng  = models.FloatField(null=True, blank=True)
    address_text  = models.CharField(max_length=500, blank=True)
    zone_name     = models.CharField(max_length=100, blank=True)

    media_urls    = models.JSONField(default=list)

    ai_confidence   = models.FloatField(default=0.0)
    fraud_score     = models.FloatField(default=0.0)
    ai_raw_response = models.JSONField(default=dict)

    vouch_count     = models.PositiveIntegerField(default=0)
    vouch_threshold = models.PositiveIntegerField(default=3)

    total_donations_kobo = models.PositiveIntegerField(default=0)
    donation_count       = models.PositiveIntegerField(default=0)

    is_infrastructure = models.BooleanField(default=False)

    agency_assigned = models.ForeignKey(
        'organisations.Organisation', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='assigned_incidents'
    )

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def vouch_threshold_for_severity(self):
        return {'CRITICAL': 1, 'HIGH': 2, 'MEDIUM': 3, 'LOW': 5}.get(self.severity, 3)

    def set_vouch_threshold(self):
        self.vouch_threshold = self.vouch_threshold_for_severity
        self.save(update_fields=['vouch_threshold'])

    @property
    def total_donations_naira(self):
        return self.total_donations_kobo / 100


class ResponseLog(models.Model):
    """Immutable record of every status change. Never delete these."""
    incident    = models.ForeignKey(Incident, on_delete=models.CASCADE,
                    related_name='response_logs')
    from_status = models.CharField(max_length=20, blank=True)
    to_status   = models.CharField(max_length=20)
    actor       = models.CharField(max_length=200)
    note        = models.TextField(blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class VouchRecord(models.Model):
    """One vouch per session per incident. unique_together prevents duplicates."""
    incident      = models.ForeignKey(Incident, on_delete=models.CASCADE,
                      related_name='vouches')
    session_hash  = models.CharField(max_length=64)
    voucher_lat   = models.FloatField(null=True, blank=True)
    voucher_lng   = models.FloatField(null=True, blank=True)
    distance_km   = models.FloatField(null=True, blank=True)
    is_suspicious = models.BooleanField(default=False)
    source        = models.CharField(max_length=20,
                      choices=[('WEB', 'Web'), ('WHATSAPP', 'WhatsApp reaction')],
                      default='WEB')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('incident', 'session_hash')


class IncidentMedia(models.Model):
    """Structured media record — image or video attached to an incident."""
    MEDIA_TYPE_CHOICES = [('image', 'Image'), ('video', 'Video')]

    incident         = models.ForeignKey(Incident, on_delete=models.CASCADE,
                         related_name='media')
    media_type       = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    public_url       = models.URLField(max_length=500)
    storage_path     = models.CharField(max_length=500)
    file_size        = models.PositiveIntegerField()
    uploaded_by_hash = models.CharField(max_length=64, blank=True)
    upload_timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['upload_timestamp']
