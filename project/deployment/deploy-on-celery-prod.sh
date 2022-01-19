source ~/venv/bin/activate
cd ~/likeminds/project
git checkout master
git pull
pip3 install -r requirements.txt
deactivate
sudo systemctl restart celery
sudo systemctl status celery
