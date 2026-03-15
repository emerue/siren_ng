from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Donation

@shared_task
def donation_pending_cleanup():
    """Daily cleanup of stale PENDING donations (older than 24 hours)."""
    cutoff = timezone.now() - timedelta(hours=24)
    stale = Donation.objects.filter(status='PENDING', created_at__lt=cutoff)
    count = stale.count()
    stale.delete()
    return f"Deleted {count} stale PENDING donations."
