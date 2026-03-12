from celery import shared_task


@shared_task
def notify_nearest_responders(incident_id):
    """Phase 3: Find and notify nearest verified responders."""
    pass
