source eb-virt-v3/bin/activate
cd Togther/project
git checkout master
git pull
pip3 install -r requirements.txt
DJANGO_SETTINGS_MODULE=project.settings.production python3 manage.py makemigrations
DJANGO_SETTINGS_MODULE=project.settings.production python3 manage.py migrate
deactivate
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
