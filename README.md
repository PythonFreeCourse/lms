# Python's Course LMS

<p align="center">
  <img title="BSD-3 Clause" src="https://img.shields.io/github/license/PythonFreeCourse/LMS.svg">
  <img title="Travis (.com) branch" src="https://img.shields.io/travis/com/PythonFreeCourse/LMS/master.svg">
  <img title="LGTM Python Grade" src="https://img.shields.io/lgtm/grade/python/github/PythonFreeCourse/LMS.svg">
  <img title="LGTM JavaScript Grade" src="https://img.shields.io/lgtm/grade/javascript/github/PythonFreeCourse/LMS.svg">
</p>

## Project setup
```bash
git clone https://github.com/PythonFreeCourse/lms
cd lms
pip install -r --user requirements.txt
mv lmsweb/config.py.example lmsweb/config.py
echo "SECRET_KEY = \"$(python -c 'import os;print(os.urandom(32).hex())')\"" >> lmsweb/config.py

# For debug only
export FLASK_DEBUG=1
# For production, edit the rest of config.py manually

flask run
```

Enter http://127.0.0.1:5000, and the initial credentials should appear in your terminal. :)

After logging in, use https://127.0.0.1:5000/admin to modify entries in the database.
