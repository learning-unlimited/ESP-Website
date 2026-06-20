#!/bin/bash
set -e

# Add node_modules bin to PATH so lessc is available for theme compilation
export PATH="$PATH:/home/runner/workspace/esp/public/media/theme_editor/node_modules/.bin"

echo ">>> Running Django migrations..."
cd esp && python manage.py migrate --settings=esp.settings --noinput

echo ">>> Collecting static files..."
python manage.py collectstatic --settings=esp.settings --noinput -v 0

echo ">>> Compiling theme CSS..."
python manage.py recompile_theme --settings=esp.settings

echo ">>> Starting Django development server..."
python manage.py runserver 0.0.0.0:5000 --settings=esp.settings
