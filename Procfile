web: daphne -b 0.0.0.0 -p $PORT sirenapp.asgi:application
worker: celery -A sirenapp worker -l info --concurrency 2
beat: celery -A sirenapp beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
