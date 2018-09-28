# Togther

1. Install Python : ```pip install python3.6```

2. Setup Virtualenv : ```sudo pip3 install virtualenv```
                      ```virtualenv venv -p python3```
                      ```source venv/bin/activate```
                      
3. Install Django : ```pip install django==2.1```

4. Inside the virtualenv clone the repo. 

5. Setup a psql database and update the credentials in settings.py

6. migrate the database: ``` python manage.py makemigrations```
                         ``` python manage.py migrate ```
                         
7. Run django server: ``` python manage.py runserver```

  Go to `localhost:8000/togther`
  
  
Abhishek
