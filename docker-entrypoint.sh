#!/bin/bash
set -e

# Copy Docker-specific settings if local_settings.py doesn't exist
if [ ! -f /app/esp/esp/local_settings.py ]; then
    echo ">>> Creating local_settings.py from Docker template..."
    cp /app/esp/esp/local_settings.py.docker /app/esp/esp/local_settings.py
fi

# Create media symlinks if they don't exist
if [ ! -e /app/esp/public/media/images ]; then
    echo ">>> Creating media symlinks..."
    ln -sf /app/esp/public/media/default_images /app/esp/public/media/images
fi
if [ ! -e /app/esp/public/media/styles ]; then
    ln -sf /app/esp/public/media/default_styles /app/esp/public/media/styles
fi

# Wait for PostgreSQL to be ready
echo ">>> Waiting for PostgreSQL..."
until python -c "
import psycopg2
try:
    psycopg2.connect(host='db', dbname='devsite_django', user='esp', password='password')
except psycopg2.OperationalError:
    exit(1)
" 2>/dev/null; do
    sleep 2
done
echo ">>> PostgreSQL is ready!"

# Run migrations and collect static files only on first run,
# or when FORCE_SETUP=1 is set (e.g., after pulling new code).
MARKER_FILE="/app/.docker-setup-done"
if [ ! -f "$MARKER_FILE" ] || [ "${FORCE_SETUP:-0}" = "1" ]; then
    echo ">>> Running migrations..."
    python /app/esp/manage.py migrate --noinput

    echo ">>> Collecting static files..."
    python /app/esp/manage.py collectstatic --noinput -v 0

    touch "$MARKER_FILE"
else
    echo ">>> Skipping migrations and collectstatic (already done)."
    echo ">>> To force re-run, use: FORCE_SETUP=1 docker compose up"
fi

# Change to the esp directory before starting the server
# This ensures manage.py resolves Django settings correctly
cd /app/esp

echo ">>> Starting server..."
exec "$@"
