# Python's Course LMS

<p align="center">
  <img title="BSD-3 Clause" src="https://img.shields.io/github/license/PythonFreeCourse/LMS.svg">
  <img title="Travis (.com) branch" src="https://img.shields.io/travis/com/PythonFreeCourse/LMS/master.svg">
  <img title="LGTM Python Grade" src="https://img.shields.io/lgtm/grade/python/github/PythonFreeCourse/LMS.svg">
  <img title="LGTM JavaScript Grade" src="https://img.shields.io/lgtm/grade/javascript/github/PythonFreeCourse/LMS.svg">
</p>

👋 Welcome to Python course learning management system. 🐍

The system objectives - 
1. Allow teachers and mentors to input exercises list and provide feedback/comments to students exercises solutions.
2. Allow students to load their exercises solutions and get feedback to their work.

## Creating development environment
### Prerequisites
1. Linux based system - either [WSL on windows](https://docs.microsoft.com/en-us/windows/wsl/install-win10) or full blown linux.
2. [Python](https://www.python.org/downloads/release/python-385/) 
3. [Docker](https://docs.docker.com/docker-for-windows/install/) and docker-compose.

### Minimal setup
This setup is for debug purposes and will use sqlite database and frontend only.

Steps to do:
1. Clone this repository.
2. Set environment variables.
3. Run the application.

```bash
git clone https://github.com/PythonFreeCourse/lms
cd lms

export FLASK_DEBUG=1
export LOCAL_SETUP=true
export FLASK_APP=lms.lmsweb
export PYTHONPATH=`pwd`:$PYTHONPATH

cd devops
source dev_bootstrap.sh
# The initial credentials should appear in your terminal. :)

cd ..
flask run  # Run in root directory
```

After logging in, use [localhost admin](https://127.0.0.1:5000/admin) to modify entries in the database.


### Full setup
This setup will create the following items:
* Application - LMS code.
* Middleware (messaging queue) - RabbitMQ.
* Persistence database - PostgreSQL.

Steps to do:

1. Clone this repository.
2. Setup using docker & docker-compose.
3. Run the application.

```bash
git clone https://github.com/PythonFreeCourse/lms
cd lms
cp lms/lmsweb/config.py.example lms/lmsweb/config.py
echo "SECRET_KEY = \"$(python -c 'import os;print(os.urandom(32).hex())')\"" >> lms/lmsweb/config.py

cd devops
. ./build.sh && . ./start.sh && . ./bootstrap.sh && . ./i18n.sh
```

In case you want to add the stub data to PostgreSQL DB, run:
```
docker exec -it lms_http_1 bash
python lmsdb/bootstrap.py
```

Enter http://127.0.0.1:8080, and the initial credentials should appear in your terminal. :)

After logging in, use [localhost admin](https://127.0.0.1:8080/admin) to modify entries in the database.

In case you want to enable the mail system:

1. Insert your mail details in the configuration file.
2. Change the `DISABLE_MAIL` line value to False.


## Code modification check list
### Run flake8 
```
# on lms root directory
flake8 lms
```
### Run tests
```
export PYTHONPATH=`pwd`
pip install -r requirements.txt
pip install -r dev_requirements.txt
py.test -vvv
```
### Contributing
View [contributing guidelines](https://github.com/PythonFreeCourse/lms/blob/master/CONTRIBUTING.md).
