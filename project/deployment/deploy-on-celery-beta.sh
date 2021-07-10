cd togther
source venv/bin/activate
cd code/project
pip3 install -r requirements.txt
deactivate
git checkout development
git pull
sudo systemctl restart celery
sudo systemctl status celery
