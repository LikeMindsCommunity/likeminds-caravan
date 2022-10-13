#!/bin/bash

source /etc/environment

APPLICATION_NAME=$PROJECT_NAME
APPLICATION_ENVIRONMENT=$PROJECT_ENVIRONMENT
APPLICATION_AWS_S3_BUCKET=$PROJECT_AWS_S3_BUCKET
APPLICATION_DOT_ENV_KEY=$PROJECT_AWS_S3_DOT_ENV_KEY
APPLICATION_LOCATION=$PROJECT_LOCATION
APPLICATION_DOT_ENV_LOCATION=$PROJECT_DOT_ENV_LOCATION
APPLICATION_REQUIREMENTS_LOCATION=$PROJECT_REQUIREMENTS
APPLICATION_VENV_LOCATION=$PROJECT_VENV
APPLICATION_MANAGE_SCRIPT_LOCATION=$PROJECT_MANAGE_SCRIPT

print_internal() {
    PREFIX="\n\n **** "
    SUFFIX=" **** \n\n"
    STR="$PREFIX $1 $SUFFIX"
    printf "$STR"
}

get_project_branch_latest() {
  cd "$APPLICATION_LOCATION" || exit

  if [ "$APPLICATION_ENVIRONMENT" == "BETA" ]
  then

    print_internal "pull branch origin/development"
    git checkout development
    git pull
    print_internal "latest refs pull success"

  elif [ "$APPLICATION_ENVIRONMENT" == "PRODUCTION" ]
  then

    print_internal "pull branch origin/master"
    git checkout master
    git pull
    print_internal "latest refs pull success"

  else
    print_internal "Unknown application environment $APPLICATION_ENVIRONMENT"
  fi

  cd ~ || exit
}

get_project_dot_env() {
  print_internal "get and write dot env into project folder"
  print_internal "writing file at $APPLICATION_DOT_ENV_LOCATION"
  aws s3api get-object --bucket "$APPLICATION_AWS_S3_BUCKET" --key "$APPLICATION_DOT_ENV_KEY" "$APPLICATION_DOT_ENV_LOCATION"
  print_internal "wrote dot env into project"
}

activate_project_venv() {
  print_internal "activating environment"
  source "$APPLICATION_VENV_LOCATION"
  print_internal "environment at $APPLICATION_VENV_LOCATION activate success"
}

install_project_requirements() {
  print_internal "install project requirements"
  pip3 install -r "$APPLICATION_REQUIREMENTS_LOCATION"
  print_internal "project requirements install success"
}

migrate_database() {
  print_internal "migrating database"

  if [ "$APPLICATION_NAME" == "CARAVAN" ]
  then
    migrate_database_internal
  elif [ "$APPLICATION_NAME" == "CARAVAN-CELERY" ]
  then
    print_internal "database migration not required for $APPLICATION_NAME"
  else
    print_internal "Unknown application $APPLICATION_NAME"
  fi
}

migrate_database_internal() {
  cd "$APPLICATION_LOCATION" || exit

  if [ "$APPLICATION_ENVIRONMENT" == "BETA" ]
  then

    print_internal "make and perform database migrations"
    DJANGO_SETTINGS_MODULE=project.settings.beta python3 "$APPLICATION_MANAGE_SCRIPT_LOCATION" makemigrations
    DJANGO_SETTINGS_MODULE=project.settings.beta python3 "$APPLICATION_MANAGE_SCRIPT_LOCATION" migrate
    print_internal "database migration success"

  elif [ "$APPLICATION_ENVIRONMENT" == "PRODUCTION" ]
  then

    print_internal "make and perform database migrations"
    DJANGO_SETTINGS_MODULE=project.settings.production python3 "$APPLICATION_MANAGE_SCRIPT_LOCATION" makemigrations
    DJANGO_SETTINGS_MODULE=project.settings.production python3 "$APPLICATION_MANAGE_SCRIPT_LOCATION" migrate
    print_internal "database migration success"

  else
    print_internal "Unknown application environment $APPLICATION_ENVIRONMENT"
  fi

  cd ~ || exit
}

deactivate_project_venv() {
  print_internal "deactivate environment"
  deactivate
}

start_application() {
  print_internal "starting application"

  if [ "$APPLICATION_NAME" == "CARAVAN" ]
  then
    start_application_server_internal
  elif [ "$APPLICATION_NAME" == "CARAVAN-CELERY" ]
  then
    start_application_celery_server_internal
  else
    print_internal "Unknown application $APPLICATION_NAME"
  fi
}

start_application_server_internal() {
  print_internal "starting application server"
  sudo systemctl restart gunicorn
  sudo systemctl status gunicorn
  print_internal "application server start success"
}

start_application_celery_server_internal() {
  print_internal "starting application server"
  sudo systemctl restart celery
  sudo systemctl status celery
  sudo systemctl restart celery_beat
  sudo systemctl status celery_beat
  print_internal "application server start success"
}

deploy() {

  print_internal "deploying $APPLICATION_NAME to $HOSTNAME"

  get_project_branch_latest
  get_project_dot_env
  activate_project_venv
  install_project_requirements
  migrate_database
  deactivate_project_venv
  start_application

  print_internal "deployed $APPLICATION_NAME to $HOSTNAME"
}

deploy
