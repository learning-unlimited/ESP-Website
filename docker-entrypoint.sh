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

# Refresh theme node_modules when the named volume is stale.
# Named volumes persist across `docker compose up --build` and will not
# automatically receive new packages (e.g. sass) added to package.json.
# The Dockerfile bakes a versioned copy at /opt/theme_node_modules_baked/
# with a .lock-hash file. Compare that hash to a marker in the live volume;
# if they differ, restore from the baked copy (no npm needed at runtime).
THEME_DIR=/app/esp/public/media/theme_editor
THEME_NM="$THEME_DIR/node_modules"
VOL_HASH_FILE="$THEME_NM/.lock-hash"
BAKED_DIR="/opt/theme_node_modules_baked"
BAKED_HASH_FILE="$BAKED_DIR/.lock-hash"
if [ -f "$BAKED_HASH_FILE" ]; then
    BAKED_HASH=$(cat "$BAKED_HASH_FILE")
    STORED_HASH=$(cat "$VOL_HASH_FILE" 2>/dev/null || echo "")
    if [ "$BAKED_HASH" != "$STORED_HASH" ]; then
        echo ">>> Theme node_modules stale — restoring from baked image copy..."
        cp -r "$BAKED_DIR/." "$THEME_NM/"
        echo ">>> Theme node_modules restored."
    fi
fi

# Change to the esp directory before starting the server
# This ensures manage.py resolves Django settings correctly
cd /app/esp

echo ">>> Starting server..."
exec "$@"
