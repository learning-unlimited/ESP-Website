#!/bin/bash
set -e

echo ">>> Running Django migrations..."
cd esp && python manage.py migrate --settings=esp.settings --noinput

echo ">>> Collecting static files..."
python manage.py collectstatic --settings=esp.settings --noinput -v 0

echo ">>> Starting Django development server..."
python manage.py runserver 0.0.0.0:5000 --settings=esp.settings
