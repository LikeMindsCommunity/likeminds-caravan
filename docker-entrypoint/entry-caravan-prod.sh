source /opt/venv/bin/activate
cd ./project
export DJANGO_SETTINGS_MODULE=project.settings.production
exec gunicorn --workers=3 --timeout=30 --bind 0.0.0.0:8081 --log-level debug project.wsgi