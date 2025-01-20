source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.load gunicorn --workers=4 --threads=10 --log-level debug --bind 0.0.0.0:8081 project.wsgi