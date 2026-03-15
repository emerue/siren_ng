release: python manage.py migrate
web: daphne -b 0.0.0.0 -p $PORT sirenapp.asgi:application
worker: celery -A sirenapp worker -l info
beat: celery -A sirenapp beat -l info
