source /opt/venv/bin/activate
cd ./project
DJANGO_SETTINGS_MODULE=project.settings.development python3 manage.py makemigrations
DJANGO_SETTINGS_MODULE=project.settings.development python3 manage.py migrate
DJANGO_SETTINGS_MODULE=project.settings.development gunicorn --bind 0.0.0.0:8081 project.wsgi