cd likeminds
source bin/activate
cd project
pip3 install -r requirements.txt
deactivate
git checkout development
git pull
cd ../
source bin/activate
cd project
DJANGO_SETTINGS_MODULE=project.settings.beta python3 manage.py makemigrations
DJANGO_SETTINGS_MODULE=project.settings.beta python3 manage.py migrate
deactivate
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
