import json
from datetime import datetime
from urllib.parse import urljoin, urlparse

import flask
from flask import render_template, request, url_for

from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.datastructures import FileStorage

from lms.lmsweb import webapp
from lms.lmsweb.models import User, Solution, Exercise

from werkzeug.utils import redirect

login_manager = LoginManager()
login_manager.init_app(webapp)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'

PERMISSIVE_CORS = {
}


@webapp.after_request
def after_request(response):
    for name, value in PERMISSIVE_CORS.items():
        response.headers.add(name, value)
    return response


@login_manager.user_loader
def load_user(user_id):
    return User.get_or_none(id=user_id)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return (
            test_url.scheme in ('http', 'https')
            and ref_url.netloc == test_url.netloc
    )


def redirect_logged_in(func):
    """Must wrap the route"""

    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('main'))
        else:
            return func(*args, **kwargs)

    return wrapper


@redirect_logged_in
@webapp.route('/login', methods=['GET', 'POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.get_or_none(username=username)

    if user is not None and user.is_password_valid(password):
        login_user(user)
        next_url = request.args.get('next_url')
        if not is_safe_url(next_url):
            return flask.abort(400)
        return redirect(next_url or url_for('main'))

    return render_template('login.html')


@webapp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('login')


@webapp.route('/')
@login_required
def main():
    return render_template('exercises.html')


@webapp.route('/send')
@login_required
def send():
    return render_template('upload.html')


@webapp.route('/upload', methods=['POST'])
def upload():
    # TODO: Save the files WITHOUT EXECUTION PERMISSIONS
    # TODO: Check that the file is ipynb/py
    # TODO: Extract the right exercise from the notebook
    #       (ask Efrat for code)
    # TODO: Check max filesize of (max notebook size + 20%)
    exercise = Exercise.get_by_id(request.form.get('exercise', 0))
    if not exercise:
        # handle error
        raise ValueError("exercise does not exist")
    user = User.get_by_id(request.form.get('user', 0))
    if not user:
        # handle error
        raise ValueError("invalid user")
    file: FileStorage = request.files.get('file')
    if not file:
        # handle error
        raise ValueError("no file was given")
    json_file_data = file.read()
    file_content = json.loads(json_file_data)
    if 'cells' not in file_content:
        # handle error
        raise ValueError("Invalid file format - must be ipynb")

    Solution.create(
        exercise=exercise,
        solver=user,
        submission_timestamp=datetime.now(),
        json_data_str=json_file_data,
    )
    return 'yay'


@webapp.route('/view')
def view():
    return render_template('view.html')
