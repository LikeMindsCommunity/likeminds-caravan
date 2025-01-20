source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.load gunicorn --workers=1 --threads=4 --log-level debug --bind 0.0.0.0:8081 project.wsgi