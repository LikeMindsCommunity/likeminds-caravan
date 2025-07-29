source /opt/venv/bin/activate
cd ./project
export DJANGO_SETTINGS_MODULE=project.settings.production
exec gunicorn --workers=4 --timeout=30 --bind 0.0.0.0:8081 project.wsgi
