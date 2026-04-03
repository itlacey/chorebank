web: gunicorn chorebank.wsgi --bind 0.0.0.0:$PORT
worker: python manage.py qcluster
release: python manage.py migrate && python manage.py collectstatic --noinput && python manage.py seed_users && python manage.py setup_schedules
