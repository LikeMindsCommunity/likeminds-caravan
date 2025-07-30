mkdir /var/log/celery
touch /var/log/celery/celery.log
touch /var/log/celery/celery_beat.log
source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.production celery -A project worker --loglevel=info -Q celery --concurrency=6
DJANGO_SETTINGS_MODULE=project.settings.production celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler -Q celery
