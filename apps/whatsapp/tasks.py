from celery import shared_task


@shared_task
def notify_reporter_verified(incident_id):
    """Phase 2: Send WhatsApp tracking link to reporter."""
    pass


@shared_task
def notify_reporter_rejected(incident_id, reason):
    """Phase 2: Notify reporter their report was rejected."""
    pass


@shared_task
def notify_reporter_verifying(incident_id):
    """Phase 2: Notify reporter their report is being verified."""
    pass


@shared_task
def post_community_announcement(incident_id):
    """Phase 2: Post to zone WhatsApp group."""
    pass
