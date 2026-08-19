#!/bin/bash
set -euo pipefail

echo "Running collectstatic..."
python manage.py collectstatic --noinput || echo "WARNING: collectstatic failed, continuing..."

# Migrations must succeed before we serve traffic.
#
# This previously ended in `|| echo "WARNING: migrate failed"`, so a database
# outage produced a container that started happily and then failed every single
# query. Production served a broken API for days while looking deployed.
#
# Retry a few times to ride out a transient blip on deploy, then fail the
# deploy loudly so Railway surfaces it and keeps the last good version.
MIGRATE_ATTEMPTS="${MIGRATE_ATTEMPTS:-5}"
MIGRATE_DELAY="${MIGRATE_DELAY:-10}"

migrated=0
for attempt in $(seq 1 "$MIGRATE_ATTEMPTS"); do
  echo "Running migrations (attempt $attempt/$MIGRATE_ATTEMPTS)..."
  if python manage.py migrate --noinput; then
    migrated=1
    break
  fi
  if [ "$attempt" -lt "$MIGRATE_ATTEMPTS" ]; then
    echo "migrate failed; retrying in ${MIGRATE_DELAY}s..."
    sleep "$MIGRATE_DELAY"
  fi
done

if [ "$migrated" -ne 1 ]; then
  echo "FATAL: migrations failed after ${MIGRATE_ATTEMPTS} attempts."
  echo "The database is unreachable or DATABASE_URL is wrong."
  echo "Refusing to start: serving traffic now would 500 on every query."
  exit 1
fi

echo "Starting Daphne server..."
exec daphne -b 0.0.0.0 -p "${PORT:-8080}" sirenapp.asgi:application
