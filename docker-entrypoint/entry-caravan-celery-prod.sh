mkdir /var/log/celery
touch /var/log/celery/celery.log
touch /var/log/celery/celery_beat.log
source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.production celery -A project worker -P eventlet -c 6 --max-tasks-per-child=20 --loglevel=info -Q celery
DJANGO_SETTINGS_MODULE=project.settings.production celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler -Q celery
