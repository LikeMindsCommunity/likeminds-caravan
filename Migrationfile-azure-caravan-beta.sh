#!/bin/bash

APPLICATION_ENVIRONMENT="BETA"
APPLICATION_DOT_ENV_LOCATION="/home/apps/caravan-beta/Togther/project/project/settings/.env"
APPLICATION_LOCATION="/home/apps/caravan-beta/Togther/project/"
APPLICATION_MANAGE_SCRIPT_LOCATION="/home/apps/caravan-beta/Togther/project/manage.py"
APPLICATION_NAME="CARAVAN"
APPLICATION_REQUIREMENTS_LOCATION="/home/apps/caravan-beta/Togther/project/requirements.txt"
APPLICATION_VENV_LOCATION="/home/apps/caravan-beta/caravan-beta-venv/bin/activate"
APPICATION_ACCOUNT_NAME="likemindsstagingstorage"
APPLICATION_CONTAINER_NAME="likeminds-staging-configs"
APPLICATION_DOT_ENV_BLOB_NAME="caravan-beta/caravan-beta-dot-env-private"

print_internal() {
    PREFIX="\n\n **** "
    SUFFIX=" **** \n\n"
    STR="$PREFIX $1 $SUFFIX"
    printf "$STR"
}

get_project_dot_env() {
  print_internal "get and write dot env into project folder"
  print_internal "writing file at $APPLICATION_DOT_ENV_LOCATION"

  echo $AZURE_CREDENTIALS > azure_credentials.json
  az login --service-principal --username "$(jq -r .clientId azure_credentials.json)" --password "$(jq -r .clientSecret azure_credentials.json)" --tenant "$(jq -r .tenantId azure_credentials.json)"
  az storage blob download --account-name $APPICATION_ACCOUNT_NAME --container-name $APPLICATION_CONTAINER_NAME --name $APPLICATION_DOT_ENV_BLOB_NAME --file $APPLICATION_DOT_ENV_LOCATION --auth-mode login

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

  if [ "$APPLICATION_ENVIRONMENT" == "BETA" ]
  then

    print_internal "make and perform database migrations"
    DJANGO_SETTINGS_MODULE=project.settings.beta python3 "$APPLICATION_MANAGE_SCRIPT_LOCATION" makemigrations
    DJANGO_SETTINGS_MODULE=project.settings.beta python3 "$APPLICATION_MANAGE_SCRIPT_LOCATION" migrate
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

  print_internal "migrating caravan-beta database.."

  get_project_dot_env
  activate_project_venv
  install_project_requirements
  migrate_database
  deactivate_project_venv

  print_internal "migrated caravan-beta database.."
}

migrate
