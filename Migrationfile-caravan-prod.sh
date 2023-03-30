#!/bin/bash

APPLICATION_ENVIRONMENT="PRODUCTION"
APPLICATION_DOT_ENV_LOCATION="/home/apps/caravan-prod/Togther/project/project/settings/.env"
APPLICATION_DOT_ENV_REMOTE_LOCATION="https://prod-likeminds-media.s3.ap-south-1.amazonaws.com/environment/caravan-prod-dot-env-public"
APPLICATION_LOCATION="/home/apps/caravan-prod/Togther/project/"
APPLICATION_MANAGE_SCRIPT_LOCATION="/home/apps/caravan-prod/Togther/project/manage.py"
APPLICATION_NAME="CARAVAN"
APPLICATION_REQUIREMENTS_LOCATION="/home/apps/caravan-prod/Togther/project/requirements.txt"
APPLICATION_VENV_LOCATION="/home/apps/caravan-prod/caravan-prod-venv/bin/activate"

print_internal() {
    PREFIX="\n\n **** "
    SUFFIX=" **** \n\n"
    STR="$PREFIX $1 $SUFFIX"
    printf "$STR"
}

get_project_branch_latest() {
  cd "$APPLICATION_LOCATION" || exit

  if [ "$APPLICATION_ENVIRONMENT" == "PRODUCTION" ]
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

  wget -O $APPLICATION_DOT_ENV_LOCATION $APPLICATION_DOT_ENV_REMOTE_LOCATION

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
  else
    print_internal "Unknown application $APPLICATION_NAME"
  fi
}

migrate_database_internal() {
  cd "$APPLICATION_LOCATION" || exit

  if [ "$APPLICATION_ENVIRONMENT" == "PRODUCTION" ]
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

migrate() {

  print_internal "migrating caravan-prod database.."

  get_project_branch_latest
  get_project_dot_env
  activate_project_venv
  install_project_requirements
  migrate_database
  deactivate_project_venv

  print_internal "migrated caravan-prod database.."
}

migrate
