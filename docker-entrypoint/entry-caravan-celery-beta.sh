mkdir /var/log/celery
touch /var/log/celery/celery.log
touch /var/log/celery/celery_beat.log
source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.beta celery -A project worker --loglevel=info -f /var/log/celery/celery.log
DJANGO_SETTINGS_MODULE=project.settings.beta celery -A project beat --loglevel=info -f /var/log/celery/celery_beat.log --scheduler django_celery_beat.schedulers:DatabaseScheduler
