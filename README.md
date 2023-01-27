# Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

## Prerequisites
``` 
Python 3.7.15
Postgres
Redis
RabbitMQ
Elasticsearch
```

## Installation
1. Install Python by running the following command:
``` 
pip install python3.7 
```
2. Setup Virtual environment by running the following commands:
```
python3 -m venv lm-env
```
3. Activate your virtual environment by running follow commands:
```
source venv/bin/activate 
```

4. Inside the virtualenv clone the repo.


3. Go to the project directory:
```
cd project
```
4. Install dependencies by running the following command:
```
pip install -r requirements.txt
```
5. Make sure you have all of the prerequisites installed/setup on your machine, including Postgres, Redis, RabbitMQ, and Elasticsearch and are running in the background.

6. Make an .env file and place it under the directory -  
```
project/
```

7. Create a new Postgres database and update the DB credentials in the .env file. 

8. Create a folder named logs under utility & create a file named collabmates.log in it.
```
mkdir utility/logs
touch utility/logs/collabmates.log
```
9. Apply database migrations:
```
python manage.py makemigrations
python manage.py migrate
```
10. Run the Django server:
```
python manage.py runserver
```
11. Your application should now be running on http://localhost:8000.

### Additional Information
This project uses Django, a high-level Python web framework, and various other packages, which are listed in the requirements.txt file.
This project is using virtualenv to create isolated Python environments. It is recommended to use virtualenv to avoid any conflicts with system-wide packages.
This project is using Postgres as a database.
This project is using Redis, RabbitMQ, and Elasticsearch for caching, message queueing and search functionality.
This project is using Django's built-in database migration functionality to handle changes to the database schema over time.