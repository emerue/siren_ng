#!/bin/bash

echo "Running collectstatic..."
python manage.py collectstatic --noinput || echo "WARNING: collectstatic failed, continuing..."



echo "Running migrations..."
python manage.py migrate --noinput || echo "WARNING: migrate failed — check DATABASE_URL in Railway env vars"

# Create superuser if it doesn't exist
# python manage.py shell -c "
# from django.contrib.auth import get_user_model
# U = get_user_model()
# if not U.objects.filter(username='admin').exists():
#     U.objects.create_superuser('admin', 'admin@siren.ng', 'siren-admin-ng')
#     print('Superuser created')
# else:
#     print('Superuser already exists')
# "


echo "Starting Daphne server..."
exec daphne -b 0.0.0.0 -p ${PORT:-8080} sirenapp.asgi:application


