from celery import shared_task


@shared_task
def notify_nearest_organisations(incident_id):
    """Phase 3: Find and notify nearest verified organisations."""
    pass
