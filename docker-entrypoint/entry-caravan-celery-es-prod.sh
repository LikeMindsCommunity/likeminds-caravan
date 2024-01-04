mkdir /var/log/celery
touch /var/log/celery/celery.log
touch /var/log/celery/celery_beat.log
source /opt/venv/bin/activate
cd ./project

# Exporting the env variables from file
set -a
. ./project/settings/.env
set +a

DJANGO_SETTINGS_MODULE=project.settings.production celery -A project worker --loglevel=info -Q "${ELASTIC_SEARCH_QUEUE_NAME}"
DJANGO_SETTINGS_MODULE=project.settings.production celery -A project beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler -Q "${ELASTIC_SEARCH_QUEUE_NAME}"
