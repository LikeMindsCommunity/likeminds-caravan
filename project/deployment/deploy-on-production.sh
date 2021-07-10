source eb-virt-v3/bin/activate
cd Togther/project
pip3 install -r requirements.txt
deactivate
#git checkout master
git pull
source ~/eb-virt-v3/bin/activate
DJANGO_SETTINGS_MODULE=project.settings.production python3 manage.py makemigrations
DJANGO_SETTINGS_MODULE=project.settings.production python3 manage.py migrate
deactivate
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
