#!/bin/sh
set -eu

PORT="${PORT:-10000}"

echo "[LabVault startup] Collecting static assets..."
python manage.py collectstatic --noinput

echo "[LabVault startup] Starting Gunicorn WSGI server on port ${PORT}..."
exec gunicorn labvault_project.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
