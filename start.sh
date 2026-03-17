#!/bin/bash

echo "Running collectstatic..."
python manage.py collectstatic --noinput || echo "WARNING: collectstatic failed, continuing..."

echo "Running migrations..."
python manage.py migrate --noinput || echo "WARNING: migrate failed — check DATABASE_URL in Railway env vars"

echo "Starting Daphne server..."
exec daphne -b 0.0.0.0 -p ${PORT:-8080} sirenapp.asgi:application
