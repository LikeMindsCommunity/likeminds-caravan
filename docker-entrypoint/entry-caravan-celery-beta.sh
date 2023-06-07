mkdir /var/log/celery
touch /var/log/celery/celery.log
touch /var/log/celery/celery_beat.log
source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.beta celery -A project worker --beat --loglevel=info -f /var/log/celery/celery.log
