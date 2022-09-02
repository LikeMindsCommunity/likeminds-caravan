#!/bin/bash
source /etc/environment
APP_TO_DEPLOY=$APP_NAME

NEWLINE_X2="\n\n"

if [ "$APP_TO_DEPLOY" == "CARAVAN" ]
then

printf "$NEWLINE_X2 **** deploying $APP_TO_DEPLOY to $HOSTNAME **** $NEWLINE_X2"
printf "$NEWLINE_X2 **** go to project root and activate environment **** $NEWLINE_X2"
cd /home/ec2-user/likeminds/ || exit
source bin/activate
printf "$NEWLINE_X2 **** environment activate success **** $NEWLINE_X2"

printf "$NEWLINE_X2 **** pull branch origin/development **** $NEWLINE_X2"
git checkout development
git pull
printf "$NEWLINE_X2 **** latest refs pull success **** $NEWLINE_X2"

printf "$NEWLINE_X2 **** install project requirements **** $NEWLINE_X2"
cd project || exit
pip3 install -r requirements.txt
printf "$NEWLINE_X2 **** project requirements install success **** $NEWLINE_X2"

printf "$NEWLINE_X2 **** make and perform database migrations **** $NEWLINE_X2"
DJANGO_SETTINGS_MODULE=project.settings.beta python3 manage.py makemigrations
DJANGO_SETTINGS_MODULE=project.settings.beta python3 manage.py migrate
printf "$NEWLINE_X2 **** database migration success **** $NEWLINE_X2"

printf "$NEWLINE_X2 **** deactivate environment **** $NEWLINE_X2"
deactivate

printf "$NEWLINE_X2 **** starting application server **** $NEWLINE_X2"
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
printf "$NEWLINE_X2 **** application server start success **** $NEWLINE_X2"

elif [ "$APP_TO_DEPLOY" == "CARAVAN-CELERY" ]
then

printf "$NEWLINE_X2 **** deploying $APP_TO_DEPLOY to $HOSTNAME **** $NEWLINE_X2"
printf "$NEWLINE_X2 **** go to project root and activate environment **** $NEWLINE_X2"
cd /home/ec2-user/togther/ || exit
source venv/bin/activate
printf "$NEWLINE_X2 **** environment activate success **** $NEWLINE_X2"

printf "$NEWLINE_X2 **** pull branch origin/development **** $NEWLINE_X2"
cd code/project || exit
git checkout development
git pull
printf "$NEWLINE_X2 **** latest refs pull success **** $NEWLINE_X2"

printf "$NEWLINE_X2 **** install project requirements **** $NEWLINE_X2"
pip3 install -r requirements.txt
printf "$NEWLINE_X2 **** project requirements install success **** $NEWLINE_X2"

printf "$NEWLINE_X2 **** deactivate environment **** $NEWLINE_X2"
deactivate

printf "$NEWLINE_X2 **** starting application server **** $NEWLINE_X2"
sudo systemctl restart celery
sudo systemctl status celery
sudo systemctl restart celery_beat
sudo systemctl status celery_beat
printf "$NEWLINE_X2 **** application server start success **** $NEWLINE_X2"

else
  echo "Unknown application"
fi