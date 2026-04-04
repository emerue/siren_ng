#!/bin/bash
echo "Starting Celery worker..."
exec celery -A sirenapp worker --loglevel=info
