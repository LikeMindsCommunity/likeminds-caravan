cd togther
source venv/bin/activate
cd code/project
git checkout development
git pull
pip3 install -r requirements.txt
deactivate
sudo systemctl restart celery
sudo systemctl status celery
