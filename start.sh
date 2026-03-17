#!/bin/bash
set -e

echo "Running collectstatic..."
python manage.py collectstatic --noinput

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting Daphne server..."
exec daphne -b 0.0.0.0 -p ${PORT:-8080} sirenapp.asgi:application
