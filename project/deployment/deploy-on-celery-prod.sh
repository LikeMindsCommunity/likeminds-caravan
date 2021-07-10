source ~/venv/bin/activate
cd ~/likeminds/project
pip3 install -r requirements.txt
deactivate
git checkout master
git pull
sudo systemctl restart celery
sudo systemctl status celery
