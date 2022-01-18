cd likeminds
source bin/activate
cd project
git checkout development
git pull
pip3 install -r requirements.txt
DJANGO_SETTINGS_MODULE=project.settings.beta python3 manage.py makemigrations
DJANGO_SETTINGS_MODULE=project.settings.beta python3 manage.py migrate
deactivate
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
