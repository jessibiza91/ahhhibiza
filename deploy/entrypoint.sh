#!/bin/sh
set -e

chown -R appuser:appuser /app/media /app/staticfiles

python manage.py migrate --noinput
python manage.py init_admin
python manage.py collectstatic --noinput

exec su -s /bin/sh appuser -c "exec gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers ${AHHH_GUNICORN_WORKERS:-3} --timeout 120"
