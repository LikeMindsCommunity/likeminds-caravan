source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.beta gunicorn --workers=5 --bind 0.0.0.0:8081 project.wsgi
