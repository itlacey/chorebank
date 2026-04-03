web: gunicorn chorebank.wsgi:application --bind 0.0.0.0:$PORT
worker: python manage.py qcluster
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput && python manage.py seed_users && python manage.py setup_schedules
