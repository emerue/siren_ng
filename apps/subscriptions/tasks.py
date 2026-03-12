from celery import shared_task


@shared_task
def notify_location_subscribers(incident_id):
    """Phase 5: Alert subscribers near the incident location."""
    pass
