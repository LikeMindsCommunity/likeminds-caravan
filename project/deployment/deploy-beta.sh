#!/bin/bash

cd /home/ec2-user/likeminds/
source bin/activate

cd project
pip3 install -r requirements.txt

DJANGO_SETTINGS_MODULE=project.settings.beta python3 manage.py makemigrations
DJANGO_SETTINGS_MODULE=project.settings.beta python3 manage.py migrate

deactivate

sudo systemctl restart gunicorn