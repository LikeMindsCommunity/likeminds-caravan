source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.beta gunicorn --bind 0.0.0.0:8081 project.wsgi
