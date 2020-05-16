# Python's Course LMS

<p align="center">
  <img title="BSD-3 Clause" src="https://img.shields.io/github/license/PythonFreeCourse/LMS.svg">
  <img title="Travis (.com) branch" src="https://img.shields.io/travis/com/PythonFreeCourse/LMS/master.svg">
  <img title="LGTM Python Grade" src="https://img.shields.io/lgtm/grade/python/github/PythonFreeCourse/LMS.svg">
  <img title="LGTM JavaScript Grade" src="https://img.shields.io/lgtm/grade/javascript/github/PythonFreeCourse/LMS.svg">
</p>

## Project minimized setup (sqlite & FE only)
```bash
git clone https://github.com/PythonFreeCourse/lms
cd lms
pip install --user -r lms/requirements.txt
mv lms/lmsweb/config.py.example lms/lmsweb/config.py
echo "SECRET_KEY = \"$(python -c 'import os;print(os.urandom(32).hex())')\"" >> lms/lmsweb/config.py

# For debug only
export FLASK_DEBUG=1
export LOCAL_SETUP=true

gunicorn --bind 0.0.0.0:5000 --workers 5 lms.lmsweb
```

Enter http://127.0.0.1:5000, and the initial credentials should appear in your terminal. :)

After logging in, use https://127.0.0.1:5000/admin to modify entries in the database.


## Full setup
```bash
Note: you should have docker + docker-compose installed on your computer

git clone https://github.com/PythonFreeCourse/lms
cd lms
mv lms/lmsweb/config.py.example lms/lmsweb/config.py
echo "SECRET_KEY = \"$(python -c 'import os;print(os.urandom(32).hex())')\"" >> lms/lmsweb/config.py

./devops/build.sh
./devops/start.sh
./devops/bootstrap.sh
```
```
In case you want to add the stub data to postgres db, run:
docker exec -it lms_http_1 bash
python lmsdb/bootstrap.py
```

Enter http://127.0.0.1:8080, and the initial credentials should appear in your terminal. :)

After logging in, use https://127.0.0.1:8080/admin to modify entries in the database.


## Dev checks to run
* Run flake8
```
# on lms root directory
flake8 lms
```
* run tests
```
export PYTHONPATH=`pwd`
pip install -r lms/requirements.txt
pip install -r dev_requirements.txt
py.test -vvv
```
