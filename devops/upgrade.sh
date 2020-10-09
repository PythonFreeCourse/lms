upgrade () {
  sudo chown -R $USER:$USER /opt/lms /opt/notebooks-tests
  cd /opt/notebooks-tests || { echo "cd failed"; exit 127; }
  git reset --hard
  git pull origin
  git checkout master

  cd /opt/lms || { echo "cd failed"; exit 127; }
  git reset --hard
  git pull origin
  git checkout master


  sudo systemctl stop nginx
  docker exec -t lms_db_1 pg_dump -c -U lmsweb lms > /home/$USER/dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql
  cd devops || { echo "cd failed"; exit 127; }
  source ./build.sh
  sudo systemctl restart lms
  sudo systemctl start nginx
  source ./i18n.sh
  source ./bootstrap.sh
}
