#!/bin/bash
set -e

# Copy Docker-specific settings if local_settings.py doesn't exist
if [ ! -f /app/esp/esp/local_settings.py ]; then
    echo ">>> Creating local_settings.py from Docker template..."
    cp /app/esp/esp/local_settings.py.docker /app/esp/esp/local_settings.py
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

# Install npm theme dependencies if missing (Bootstrap 3 + Bootswatch LESS sources).
# node_modules is gitignored, so a fresh clone/build needs this step.
NPM_MARKER="/app/esp/public/media/theme_editor/node_modules/bootstrap/less/bootstrap.less"
if [ ! -f "$NPM_MARKER" ]; then
    echo ">>> Installing npm theme dependencies (Bootstrap 3 / Bootswatch)..."
    (cd /app/esp/public/media/theme_editor && npm ci)
else
    echo ">>> npm theme dependencies already installed."
fi

# Always run migrations on container start so new migrations
# are applied automatically when switching branches or pulling code.
echo ">>> Running migrations..."
python /app/esp/manage.py migrate --noinput

# Collect static files only on first run,
# or when FORCE_SETUP=1 is set (e.g., after pulling new code).
COLLECTSTATIC_MARKER_FILE="/app/.collectstatic-done"
if [ ! -f "$COLLECTSTATIC_MARKER_FILE" ] || [ "${FORCE_SETUP:-0}" = "1" ]; then
    echo ">>> Collecting static files..."
    python /app/esp/manage.py collectstatic --noinput -v 0
    touch "$COLLECTSTATIC_MARKER_FILE"
else
    echo ">>> Skipping collectstatic (already done)."
    echo ">>> To force it to run again:"
    echo ">>> a) Delete the $COLLECTSTATIC_MARKER_FILE file."
    echo ">>> b) Run the following command:"
    echo ">>>    docker compose up"
fi

# Change to the esp directory before starting the server
# This ensures manage.py resolves Django settings correctly
cd /app/esp

echo ">>> Starting server..."
exec "$@"
