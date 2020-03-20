import secrets
from urllib.parse import urljoin, urlparse

import flask
from flask import render_template, request, session, url_for

from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from lmsweb import webapp
from lmsweb.models import User

from werkzeug.utils import redirect

login_manager = LoginManager()
login_manager.init_app(webapp)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'

PERMISSIVE_CORS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,PUT,POST,DELETE',
}


@webapp.before_first_request
def before_first_request():
    session['csrf'] = session.get('csrf', secrets.token_urlsafe(32))


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
    return render_template('exercises.html', csrf_token=session['csrf'])


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
    return 'yay'


@webapp.route('/view')
def view():
    return render_template('view.html')
